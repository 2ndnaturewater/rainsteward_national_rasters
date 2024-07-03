import arcpy
from arcpy.sa import Raster, Con
import logging
from raster_creation import common
from raster_creation.shared_methods import SharedMethods

class WaterSupply:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = common.get_config_parser()
        self.qb_source = self.config['water_supply_inputs']['qb']
        self.drought_source = self.config['water_supply_inputs']['drought']
        self.soil_source = self.config['water_supply_inputs']['soil']
        self.aquifer_source = self.config['water_supply_inputs']['aquifer']
        self.methods = SharedMethods('water_supply')
        self.methods.set_arc_envs()

    @common.time_it
    def finalize_water_supply(self, qb, drought, soil, aquifer):
        combined = self.combine_four_layers(qb, drought, soil, aquifer)
        return combined
    
    @common.time_it
    def qb(self):
        resampled = self.methods.resample_continuous_data(self.qb_source)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives
    
    @common.time_it
    def drought(self):
        projected = self.methods.project_to_albers(self.drought_source)
        raster = self.methods.convert_to_raster(projected, "DRGT_AFREQ")
        resampled = self.methods.resample_class_data(raster)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives
    
    @common.time_it
    def soil(self):
        resampled = self.methods.resample_continuous_data(self.soil_source)
        normalized = self.normalize_soils(resampled) # CHECK THE SOIL VALUES FROM THE SOILS INPUTS AND MAKE SURE THEY ALIGN WITH THE CORRECT CLASS & SCORE
        negatives = self.methods.set_nodata_negative(normalized)
        return negatives
    
    @common.time_it
    def aquifer(self):
        projected = self.methods.project_to_albers(self.aquifer_source)
        self.add_aquifer_field(projected)
        raster = self.methods.convert_to_raster(projected, "Value")
        resampled = self.methods.resample_class_data(raster)
        zeros = self.methods.set_nodata_zero(resampled)
        return zeros
    

# WATER SUPPLY SPECIFIC METHODS

    @common.time_it
    def combine_four_layers(self, layer_1, layer_2, layer_3, layer_4):
        self.logger.info("COMBINING FOUR LAYERS...")
        sum = Raster(layer_1) + Raster(layer_2) + Raster(layer_3) + Raster(layer_4)
        sum.save("{}_sum".format(self.benefit_sector))
        sum_raster = Raster(sum)
        total_raster = Con((sum_raster >= -3000) & (sum_raster <= -2900), (sum_raster + 3000) / 1, 
                    Con((sum_raster >= -2000) & (sum_raster <= -1800), (sum_raster + 2000) / 2, 
                    Con((sum_raster >= -1000) & (sum_raster <= -700), (sum_raster + 1000) / 3,
                    Con(sum_raster >= 0, (sum_raster / 4)))))
        total_raster.save("total_{}".format(self.benefit_sector))

    @common.time_it
    def normalize_soils(self, raster):
        self.logger.info("NORMALIZING SOILS...")
        output_name = "soils_normalized"
        normalized = Con(Raster(raster) == 1, 33.33, Con(Raster(raster) == 2, 0, Con(Raster(raster) == 3, 66.67, Con(Raster(raster) == 4, 100)))) # CHECK THE SOIL VALUES FROM THE SOILS INPUTS AND MAKE SURE THEY ALIGN WITH THE CORRECT CLASS & SCORE
        normalized.save(output_name)
        return normalized
    
    @common.time_it
    def add_aquifer_field(self, vector):
        self.logger.info("ADDING AQUIFER FIELD TO VECTOR...")
        arcpy.AddField_management(vector, "Value", "DOUBLE")
        arcpy.CalculateField_management(vector, "Value", 100)
        return vector