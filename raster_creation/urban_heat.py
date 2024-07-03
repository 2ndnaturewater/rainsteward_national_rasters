import arcpy
from arcpy.sa import Raster, Con, SetNull
import logging
from raster_creation import common
from raster_creation.shared_methods import SharedMethods
import os

class UrbanHeat:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.config = common.get_config_parser()
        self.ndvi_source = self.config['urban_heat_inputs']['ndvi']
        self.svi_source = self.config['urban_heat_inputs']['svi']
        self.uhi_source = self.config['urban_heat_inputs']['uhi']
        self.methods = SharedMethods('urban_heat')
        self.methods.set_arc_envs()

    @common.time_it
    def finalize_urban_heat(self, ndvi, svi, uhi):
        combined = self.methods.combine_three_layers(ndvi, svi, uhi)
        return combined

    @common.time_it
    def ndvi(self):
        resampled = self.methods.resample_continuous_data(self.ndvi_source)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        inverted = self.invert_ndvi_values(normalized)
        squished = self.methods.squish(inverted)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives
    
    @common.time_it
    def svi(self):  
        clipped = self.methods.clip_vector_to_us(self.svi_source)
        raster = self.methods.convert_to_raster(clipped, "RPL_THEMES")
        nulls = self.set_svi_values_null(raster) # SVI "no data" values in the source vector are -999. Setting to true null.
        resampled = self.methods.resample_class_data(nulls)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives
    
    @common.time_it
    def uhi(self):
        nulls = self.set_uhi_nan_values_null(self.uhi_source)
        zeros = self.set_uhi_negatives_zero(nulls)
        resampled = self.methods.resample_class_data(zeros)
        percentiles = self.methods.get_urban_area_percentiles(resampled)
        normalized = self.methods.normalize(resampled, percentiles)
        squished = self.methods.squish(normalized)
        negatives = self.methods.set_nodata_negative(squished)
        return negatives
    
# URBAN HEAT SPECIFIC METHODS
    
    @common.time_it
    def set_svi_values_null(self, raster):
        self.logger.info("SETTING SVI -999 VALUES TO NULL...")
        raster_name = self.methods.get_name(raster)
        output_name = "{}_nulls".format(raster_name)
        nulls_raster = SetNull(Raster(raster) == -999, Raster(raster))
        nulls_raster.save(output_name)
        return raster
    
    @common.time_it
    def set_uhi_nan_values_null(self, raster):
        self.logger.info("CONVERTING UHI NAN TO NODATA...")
        raster_name = self.methods.get_name(raster)
        output_name = "{}_nulls".format(raster_name)
        converted = Raster(raster) * 1
        converted.save(output_name)
        return converted
    
    @common.time_it
    def set_uhi_negatives_zero(self, raster):
        self.logger.info("CONVERTING UHI NEGATIVES TO 0...")
        raster_name = self.methods.get_name(raster)
        output_name = "{}_nulls".format(raster_name)        
        zeros = Con(Raster(raster) < 0, 0, Raster(raster))
        zeros.save(output_name)
        return zeros

    @common.time_it
    def invert_ndvi_values(self, raster):
        self.logger.info("INVERTING NDVI VALUES...")
        raster_name = self.methods.get_name(raster)
        output_name = "{}_nulls".format(raster_name)        
        inverted = (100 - Raster(raster)) * -1
        inverted.save(output_name)
        return inverted




