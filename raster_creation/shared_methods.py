import arcpy
from arcpy.sa import ZonalStatisticsAsTable, Raster, Con, IsNull, SetNull
from arcpy.da import SearchCursor
import logging
from raster_creation import common
import os

class SharedMethods:
    def __init__(self, benefit_sector):
        self.logger = logging.getLogger(__name__)
        self.config = common.get_config_parser()
        self.benefit_sector = benefit_sector
        self.data_folder = self.config['directories']['data_folder']
        self.telr_snap_raster = self.config['general_inputs']['telr_snap_raster']
        self.urban_areas_raster = self.config['general_inputs']['urban_areas_raster']
        self.negatives_raster = self.config['general_inputs']['negatives_raster']
        self.zeros_raster = self.config['general_inputs']['zeros_raster']
        self.us_boundary = self.config['general_inputs']['us_boundary_vector']

    @common.time_it
    def create_gdb(self):
        gdb = arcpy.management.CreateFileGDB(self.data_folder, '{}'.format(self.benefit_sector))
        return str(gdb)

    @common.time_it
    def set_arc_envs(self):
        arcpy.env.workspace = self.create_gdb()
        arcpy.env.overwriteOutput = True
        arcpy.env.cellSize = 30
        arcpy.env.outputCoordinateSystem = "PROJCS['NAD_1983_Albers',GEOGCS['GCS_North_American_1983',DATUM['D_North_American_1983',SPHEROID['GRS_1980',6378137.0,298.257222101]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Albers'],PARAMETER['false_easting',0.0],PARAMETER['false_northing',0.0],PARAMETER['central_meridian',-96.0],PARAMETER['standard_parallel_1',29.5],PARAMETER['standard_parallel_2',45.5],PARAMETER['latitude_of_origin',23.0],UNIT['Meter',1.0]]"
        arcpy.env.snapRaster = self.telr_snap_raster
        arcpy.env.extent = self.telr_snap_raster

    @common.time_it
    def project_to_albers(self, vector):
        self.logger.info("CHECKING VECTOR PROJECTION...")
        desc = arcpy.Describe(vector)
        sr = desc.spatialReference
        if sr.factoryCode != 102008:
            self.logger.info("PROJECTING VECTOR TO USA CONTIGUOUS ALBERS EQUAL AREA CONIC...")
            vector_name = self.get_name(vector)
            output_name = "{}_projected".format(vector_name)
            vector = arcpy.Project_management(vector, output_name, "102008")
        return vector
    
    @common.time_it
    def repair_geom(self, vector):
        self.logger.info("REPAIRING GEOMETRY...")
        repaired = arcpy.RepairGeometry_management(vector)
        return repaired

    @common.time_it
    def clip_vector_to_us(self, vector):
        self.logger.info("CLIPPING VECTOR TO US BOUNDARY...")
        vector_name = self.get_name(vector)
        output_name = "{}_projected".format(vector_name)
        clipped = arcpy.Clip_analysis(vector, self.us_boundary, output_name)
        return clipped
    
    @common.time_it
    def convert_to_raster(self, vector, field_name):
        self.logger.info("CONVERTING VECTOR TO RASTER...")
        vector_name = self.get_name(vector)
        output_name = "{}_projected".format(vector_name)
        raster = arcpy.PolygonToRaster_conversion(vector, field_name, output_name, cellsize=30)
        return raster

    @common.time_it
    def resample_class_data(self, raster):
        self.logger.info("RESAMPLING TOTAL RASTER...")
        raster_name = self.get_name(raster)
        output_name = "{}_resamp".format(raster_name)
        resampled = arcpy.Resample_management(raster, output_name, 30, "NEAREST")
        return resampled
    
    @common.time_it
    def resample_continuous_data(self, raster):
        self.logger.info("RESAMPLING TOTAL RASTER...")
        raster_name = self.get_name(raster)
        output_name = "{}_resamp".format(raster_name)
        resampled = arcpy.Resample_management(raster, output_name, 30, "BILINEAR")
        return resampled  
    
    @common.time_it
    def get_urban_area_percentiles(self, raster):
        self.logger.info("GETTING URBAN AREA PERCENTILES...")
        raster_name = self.get_name(raster)
        output_name = "{}_resamp".format(raster_name)
        zonal_table = ZonalStatisticsAsTable(self.urban_areas_raster, "Value", raster, output_name, percentile_values=[99, 1]) # Normalized using the 99th and 1st percentiles in urban areas
        percentiles = {}
        with arcpy.da.SearchCursor(zonal_table, ['PCT99', 'PCT1']) as cursor:
            for row in cursor:
                percentiles['p99'] = row[0]
                percentiles['p1'] = row[1]
        return percentiles
    
    @common.time_it
    def normalize(self, raster, percentiles): 
        self.logger.info("NORMALIZING raster...")
        raster_name = self.get_name(raster)
        output_name = "{}_resamp".format(raster_name)
        p99 = percentiles['p99']
        p1 = percentiles['p1']
        self.logger.info("PERCENTILE VALUES USED TO NORMALIZE | p99: {} | p1: {}".format(p99, p1))
        normalized = (Raster(raster) - p1) / (p99 - p1) * 100
        normalized.save(output_name)
        return normalized
    
    @common.time_it
    def squish(self, raster):
        self.logger.info("SETTING VALUES TO 0 OR 100 IF BELOW OR ABOVE...")
        raster_name = self.get_name(raster)
        output_name = "{}_resamp".format(raster_name)
        squished = Con(Raster(raster) > 100, 100, Con(Raster(raster) < 0, 0, Raster(raster)))
        squished.save(output_name)
        return squished

    @common.time_it
    def set_nodata_negative(self, raster):
        self.logger.info("CONVERTING NO DATA TO -1000...")
        raster_name = self.get_name(raster)
        output_name = "{}_resamp".format(raster_name)
        negatives = Con(IsNull(Raster(raster)), self.negatives_raster, Raster(raster))
        negatives.save(output_name)
        return negatives
    
    @common.time_it
    def set_nodata_zero(self, raster):
        self.logger.info("CONVERTING NO DATA TO 0...")
        raster_name = self.get_name(raster)
        output_name = "{}_resamp".format(raster_name)
        zeros = Con(IsNull(Raster(raster)), self.zeros_raster, Raster(raster))
        zeros.save(output_name)
        return zeros
    
    @common.time_it
    def combine_three_layers(self, layer_1, layer_2, layer_3):
        self.logger.info("COMBINING LAYERS FOR {}...".format(self.benefit_sector))
        sum = Raster(layer_1) + Raster(layer_2) + Raster(layer_3)
        sum.save("{}_sum".format(self.benefit_sector))
        sum_raster = Raster(sum)
        total_raster = Con((sum_raster >= -2000) & (sum_raster <= -1900), (sum_raster + 2000) / 1, 
                    Con((sum_raster >= -1000) & (sum_raster <= -800), (sum_raster + 1000) / 2, 
                    Con((sum_raster >= 0) & (sum_raster <= 300), sum_raster / 3)))
        total_raster.save("total_{}".format(self.benefit_sector))
        return total_raster
    
    @common.time_it
    def get_name(self, layer):
        try:
            name = os.path.splitext(os.path.basename(layer))[0]
        except:
            name = arcpy.Describe(layer).name
        return name
