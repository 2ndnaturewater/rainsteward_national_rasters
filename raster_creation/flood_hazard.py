import arcpy
from arcpy.sa import Raster
import logging
from raster_creation import common
from raster_creation.shared_methods import SharedMethods

class FloodHazard:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = common.get_config_parser()
        self.flood_source = self.config['flood_hazard_inputs']['flood']
        self.pct_ex_ppt_source = self.config['flood_hazard_inputs']['pct_ex_ppt']
        self.ex_ppt_change_hist = self.config['flood_hazard_inputs']['ex_ppt_change_hist']
        self.ex_ppt_change_future = self.config['flood_hazard_inputs']['ex_ppt_change_future']
        self.methods = SharedMethods('flood_hazard')
        self.methods.set_arc_envs()

    @common.time_it
    def finalize_flood_hazard(self, flood, ppt_extreme, ppt_ex_change):
        combined = self.methods.combine_three_layers(flood, ppt_extreme, ppt_ex_change)
        return combined

    @common.time_it
    def flood(self):
        projected = self.methods.project_to_albers(self.flood_source)
        self.methods.repair_geom(projected)
        clipped = self.methods.clip_vector_to_us(projected)
        normalized = self.normalize_flood_values(clipped)
        raster = self.methods.convert_to_raster(normalized)
        resampled = self.methods.resample_class_data(raster)
        zeros = self.methods.set_nodata_zero(resampled)
        return zeros
    
    @common.time_it
    def ppt_extreme(self):
        resampled = self.methods.resample_continuous_data(self.pct_ex_ppt_source)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives
    
    @common.time_it
    def ppt_ex_change(self):
        resampled_list = [self.methods.resample_continuous_data(self.ex_ppt_change_hist), self.methods.resample_continuous_data(self.ex_ppt_change_future)]
        pct_difference = self.get_ppt_change_pct_difference(resampled_list)
        percentiles = self.methods.get_urban_area_percentiles(pct_difference)
        normalized = self.methods.normalize(pct_difference, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives

# FLOOD HAZARD SPECIFIC METHODS

    @common.time_it
    def normalize_flood_values(self, vector):
        self.logger.info("CALCULATING NORMALIZED VALUE FIELD...")
        new_field = 'raster_value_norm'
        arcpy.AddField_managementd(vector, new_field, "DOUBLE", field_alias=new_field)
        expression = "convert_values(!esri_symbology!)"
        code_block = '''def convert_values(field):
    dict = {
    0 : ['Area of Undetermined Flood Hazard', 'Area of Minimal Flood Hazard', None],
    25 : ['Area with Reduced Risk Due to Levee'],
    50 : ['0.2% Annual Chance Flood Hazard'],
    75 : ['1% Annual Chance Flood Hazard', 'Future Conditions 1% Annual Chance Flood Hazard'],
    100 : ['Special Floodway', 'Regulatory Floodway']
    }
    for key in dict:
        if field in dict[key]:
            return key'''
        arcpy.CalculateField_management(vector, new_field, expression, code_block=code_block)


    def get_ppt_change_pct_difference(self, resampled):
        self.logger.info("GETTING DIFFERENCE...")
        historic = Raster(resampled[0])
        future = Raster(resampled[1])
        output_name = "ppt_ex_change_pct_difference"
        difference_pct = (future - historic)/historic
        difference_pct.save(output_name)
        return difference_pct  