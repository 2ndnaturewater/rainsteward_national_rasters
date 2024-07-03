import arcpy
from arcpy.sa import Raster
import logging
from raster_creation import common
from raster_creation.shared_methods import SharedMethods

class WaterQuality:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = common.get_config_parser()
        self.tssb_source = self.config['water_quality_inputs']['tssb']
        self.dist_303d_source_list = [self.config['water_quality_inputs']['huc8'], self.config['water_quality_inputs']['huc10'], self.config['water_quality_inputs']['huc12'], self.config['water_quality_inputs']['dist_303d']]
        self.ind_risk_source = self.config['water_quality_inputs']['ind_risk']
        self.methods = SharedMethods('water_quality')
        self.methods.set_arc_envs()

    @common.time_it
    def finalize_water_quality(self, tssb, dist_303d, ind_risk):
        combined = self.methods.combine_three_layers(tssb, dist_303d, ind_risk)
        return combined

    @common.time_it
    def tssb(self):
        resampled = self.methods.resample_continuous_data(self.tssb_source)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives
    
    @common.time_it
    def dist_303d(self):
        projected_layers = self.project_303d_vectors()
        self.add_303d_impaired_field(projected_layers)
        huc_rasters = self.convert_hucs_to_raster(projected_layers, "impaired")
        combined = self.combine_huc_rasters(huc_rasters)
        resampled = self.methods.resample_continuous_data(combined)
        normalized = self.normalize_303d(resampled)
        negatives = self.methods.set_nodata_negative(normalized)
        return negatives
    
    @common.time_it
    def ind_risk(self):
        projected = self.methods.project_to_albers(self.ind_risk_source)
        self.add_ind_risk_field(projected)
        raster = self.methods.convert_to_raster(projected, "ind_risk")
        resampled = self.methods.resample_continuous_data(raster)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives    

# WATER QUALITY SPECIFIC METHODS

    @common.time_it
    def project_303d_vectors(self):
        self.logger.info("PROJECTING 303D VECTORS...")
        projected_layers = []
        for source in self.dist_303d_source_list:
            projected = self.methods.project_to_albers(source)
            projected_layers.append(projected)
        return projected_layers
    
    @common.time_it
    def add_303d_impaired_field(self, vectors):
        self.logger.info("ADDING IMPAIRED FIELD TO 303D VECTORS...")
        hucs = [vectors[0], vectors[1], vectors[2]]
        rad_303d = vectors[3]
        for huc in hucs:
            arcpy.AddField_management(huc, "impaired", "SHORT")
            intersecting = arcpy.SelectLayerByLocation_management(huc, "INTERSECT", rad_303d, selection_type="NEW_SELECTION")
            arcpy.CalculateField_management(intersecting, "impaired", 1)
            not_intersecting = arcpy.SelectLayerByLocation_management(huc, "INTERSECT", rad_303d, selection_type="NEW_SELECTION", invert_spatial_relationship="INVERT")
            arcpy.CalculateField_management(not_intersecting, "impaired", 0)

    @common.time_it
    def convert_hucs_to_raster(self, vectors, field):
        huc_rasters = []
        hucs = [vectors[0], vectors[1], vectors[2]]
        for huc in hucs:
            raster = self.methods.convert_to_raster(huc, field)
            huc_rasters.append(raster)
        return huc_rasters
    
    @common.time_it
    def combine_huc_rasters(self, huc_rasters):
        self.logger.info("COMBINING HUC RASTERS...")
        output_name = "huc_combined"
        combined = (huc_rasters[0] + huc_rasters[1] + huc_rasters[2])/3
        combined.save(output_name)
        return combined
    
    @common.time_it
    def normalize_303d(self, raster):
        self.logger.info("NORMALIZING dist_303d RASTER...")
        output_name = "dist_303d_norm"
        normalized = (Raster(raster) - Raster(raster).minimum) / (Raster(raster).maximum - Raster(raster).minimum) * 100
        normalized.save(output_name)
        return normalized
    
    @common.time_it
    def add_ind_risk_field(self, vector):
        self.logger.info("ADDING IND RISK FIELD...")
        arcpy.AddField_management(vector, "ind_risk", "DOUBLE")
        expression = "!NPL_PFS!+!RMP_PFS!+!TSDF_PFS!+!WF_PFS!"
        arcpy.CalculateField_management(vector, "ind_risk", expression)            
