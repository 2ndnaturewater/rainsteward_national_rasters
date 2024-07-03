import argparse
import sys
from raster_creation import common
from raster_creation.urban_heat import UrbanHeat
from raster_creation.water_quality import WaterQuality
from raster_creation.water_supply import WaterSupply
from raster_creation.flood_hazard import FloodHazard


def update_water_quality():
    config = common.get_config_parser()
    parser = argparse.ArgumentParser()
    parser.add_argument("function_name", help="name of function", type=str)
    parser.add_argument("update_layer", help="options: tssb, imp_303d, ind_risk", type=str)
    args = parser.parse_args()
    water_quality = WaterQuality()
    tssb = config['water_quality_completed']['tssb'] if args.update_layer != 'tssb' else water_quality.tssb()
    dist_303d = config['water_quality_completed']['dist_303d'] if args.update_layer != 'dist_303d' else water_quality.dist_303d()
    ind_risk = config['water_quality_completed']['ind_risk'] if args.update_layer != 'ind_risk' else water_quality.ind_risk()
    water_quality.finalize_water_quality(tssb, dist_303d, ind_risk)

def update_water_supply():
    config = common.get_config_parser()
    parser = argparse.ArgumentParser()
    parser.add_argument("function_name", help="name of function", type=str)
    parser.add_argument("update_layer", help="options: qb, drought, soil, aquifer", type=str)
    args = parser.parse_args()
    water_supply = WaterSupply()
    qb = config['water_supply_completed']['qb'] if args.update_layer != 'qb' else water_supply.qb()
    drought = config['water_supply_completed']['drought'] if args.update_layer != 'drought' else water_supply.drought()
    soil = config['water_supply_completed']['soil'] if args.update_layer != 'soil' else water_supply.soil()
    aquifer = config['water_supply_completed']['aquifer'] if args.update_layer != 'aquifer' else water_supply.aquifer()
    water_supply.finalize_water_supply(qb, drought, soil, aquifer)

def update_urban_heat():
    config = common.get_config_parser()
    parser = argparse.ArgumentParser()
    parser.add_argument("function_name", help="name of function", type=str)
    parser.add_argument("update_layer", help="options: ndvi, svi, uhi", type=str)
    args = parser.parse_args()
    urban_heat = UrbanHeat()
    ndvi = config['urban_heat_completed']['ndvi'] if args.update_layer != 'ndvi' else urban_heat.ndvi()
    svi = config['urban_heat_completed']['svi'] if args.update_layer != 'svi' else urban_heat.svi()
    uhi = config['urban_heat_completed']['uhi'] if args.update_layer != 'uhi' else urban_heat.uhi()
    urban_heat.finalize_urban_heat(ndvi, svi, uhi)

def update_flood_hazard():
    config = common.get_config_parser()
    parser = argparse.ArgumentParser()
    parser.add_argument("function_name", help="name of function", type=str)
    parser.add_argument("update_layer", help="options: flood, ppt_extreme, ppt_ex_change", type=str)
    args = parser.parse_args()
    flood_hazard = FloodHazard()
    flood = config['flood_hazard_completed']['flood'] if args.update_layer != 'flood' else flood_hazard.flood()
    ppt_extreme = config['flood_hazard_completed']['ppt_extreme'] if args.update_layer != 'ppt_extreme' else flood_hazard.ppt_extreme()
    ppt_ex_change = config['flood_hazard_completed']['ppt_ex_change'] if args.update_layer != 'ppt_ex_change' else flood_hazard.ppt_ex_change()
    flood_hazard.finalize_flood_hazard(flood, ppt_extreme, ppt_ex_change)

options = {
    'update_water_quality': update_water_quality,
    'update_water_supply': update_water_supply,
    'update_urban_heat': update_urban_heat,
    'update_flood_hazard': update_flood_hazard
}

if __name__ == '__main__':
    options[sys.argv[1]]()