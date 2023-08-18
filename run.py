import click
import subprocess
import fiona
import class_definition as cd
import os.path
import glob
import copy
import sys
import tomllib
import logging
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed

#modify it to your build path
# sys.path.append("./kinetic_partition/build")
import libkinetic_partition

ORTHO_IMG_DIR = "/data/img/"
TMP_IMG_DIR = "/data/tmp/rgb/"
try:
    os.mkdir(TMP_IMG_DIR)
except:
    pass

CJSONL_PATH = "/data/output/features"
METADATA_NL_PATH = "/dim_pipeline/resources/metadata_nl.jsonl"
ROOFLINES_OUTPUT_TMPL = "/data/tmp/features/{bid}/crop/rooflines"
BUILDING_CFG_TMPL = "/data/tmp/features/{bid}/config.toml"

GF_FLOWCHART_LIDAR = "/dim_pipeline/resources/flowcharts/reconstruct_bag.json"
GF_FLOWCHART_DIM = "/dim_pipeline/resources/flowcharts/reconstruct_bag_ortho.json"
GF_FLOWCHART_MERGE_FEATURES = "/dim_pipeline/resources/flowcharts/createMulti.json"

BLD_ID = "identificatie"

EXE_CROP = "/usr/local/bin/crop"
EXE_GEOF = "/usr/local/bin/geof"

def read_toml_config(config_path):
    with open(config_path, "rb") as f:
        data = tomllib.load(f)
    # data[]
    return data

def run_crop(config_path, verbose=False):
    args = [EXE_CROP, "-c", config_path, "--index"]
    if verbose:
        args += ["--verbose"]
    return subprocess.run(args)

def run_ortho_rooflines(building_index_file, max_workers, verbose=False):
    # generate tfw metadata on raster files?
    def read_ortho_photos(ortho_images_in, input_img_dir, args):
        file_name_list = []
        ortho_image_list = []
        n_ortho_images = len(ortho_images_in)
        i_file = 0
        for image_in in ortho_images_in:
            file_name = os.path.splitext(os.path.basename(image_in))[0]
            file_name_suffix = file_name.split("_")
            file_name_used = file_name_suffix[len(file_name_suffix) - 2] + "_" + file_name_suffix[len(file_name_suffix) - 1]
            file_name_list.append(file_name_used)
            meta_in = input_img_dir + file_name + ".tfw"

            i_file = i_file + 1
            #print("Read " + str(i_file) + " / " + str(n_ortho_images) + " ---> " + file_name)

            ortho_image = cd.OrthoPhoto()
            ortho_image.read_image_use_gdal(image_in)
            if args.tif_with_tfw:
                ortho_image.read_image_meta_from_twf(meta_in)
            else:
                ortho_image.read_image_meta_from_tif()
            ortho_image_list.append(ortho_image)
        return ortho_image_list, file_name_list
    
    def extract_rooflines(args, b_id, b_poly, i_building, n_building_files, ortho_image_list, building_polys, file_name_list):
        # if not args.parallel_processing and not args.show_progress:
        # if args.verbose:
        #     logging.info("Generating building " + str(b_id))
        # Extract single builing image
        sing_b = cd.SingleBuildingImage(b_id, args.pixel_offset)
        img_used, top_left_used, image_name_used, which_case = sing_b.get_used_images_for_poly(ortho_image_list,
                                                               building_polys.building_bbox_dict[b_id], file_name_list)
        if isinstance(img_used, list) and img_used == []:
            if args.verbose:
                logging.info(f"skipping building {b_id}, no images overlapping...")
            return 0
        sing_b.crop_image(img_used, top_left_used, building_polys.building_bbox_dict[b_id], which_case)
        sing_b.write_image(sing_b.image, TMP_IMG_DIR + image_name_used + "_" + str(b_id) + ".jpg")

        # write 2d footprints
        sing_b_img_gt_footprint = copy.deepcopy(sing_b.image)
        for poly in b_poly:
            poly.convert_from_geo_to_pix(top_left_used, sing_b.pix_size, sing_b.bbox_pix)
            if args.apply_polygon_buffer_filter:
                poly.buffering_polygon(args)
            if args.write_gt_building_image_with_footprints > 1 or \
                    (args.write_gt_building_image_with_footprints == 1 and \
                     not args.apply_polygon_buffer_filter and not args.merge_connected_building_polygons):
                poly.draw_polygon(sing_b_img_gt_footprint, args.write_gt_building_image_with_footprints)

        # perform partition to extract rooflines
        img_path_read = TMP_IMG_DIR + image_name_used + "_" + str(b_id) + ".jpg"
        sing_b.pix_points, sing_b.edges = libkinetic_partition.partition_image(img_path_read, args.lsd_scale,
                                                                               args.num_intersection,
                                                                               args.enable_regularise, args.verbose)

        # Fitler out some points and edges based on the input 2d footprints
        if args.apply_polygon_buffer_filter:
            sing_b.filter_partitions(b_poly)

        # Add points and edges from input 2d footprints
        # if args.add_footprint_to_rooflines:
        #     if args.merge_connected_building_polygons:
        #         for b_ft_id in building_polys.merged_to_original_map[i_building]:
        #             for b_ft_poly in building_polys.orig_building_polygon_dict[b_ft_id]:
        #                 b_ft_poly.convert_from_geo_to_pix(top_left_used, sing_b.pix_size, sing_b.bbox_pix)
        #                 sing_b.add_footprint_lines(b_ft_poly)
        #                 if args.write_gt_building_image_with_footprints == 1:
        #                     b_ft_poly.draw_polygon(sing_b_img_gt_footprint,
        #                                            args.write_gt_building_image_with_footprints)
        #     else:
        #         for poly in b_poly:
        #             sing_b.add_footprint_lines(poly)

        if not args.write_building_image:
            os.remove(img_path_read)

        # Assign each edge a shape for attribute parsing
        # NB i_building not used here if args.merge_connected_building_polygons==False
        used_shapes, used_polys_pix_center = sing_b.collect_centers_and_shapes(args, i_building, b_id, building_polys, top_left_used)
        sing_b.attach_shape_to_edge(used_shapes, used_polys_pix_center)

        # write footprint
        if args.write_gt_building_image_with_footprints > 0:
            sing_b.write_image(sing_b_img_gt_footprint,
                               output_img_gt_footprint_dir + image_name_used + "_" + str(b_id) + "_footprint.jpg")
        del sing_b_img_gt_footprint

        # write results to images
        sing_b_img_poly = copy.deepcopy(sing_b.image)
        sing_b.draw_partitions(sing_b_img_poly)
        sing_b.sbi_convert_from_pix_to_geo(top_left_used, sing_b.pix_size, sing_b.bbox_pix)
        # if args.write_building_image_with_rooflines:
        #     sing_b.write_image(sing_b_img_poly,
        #                        output_img_rooflines_dir + image_name_used + "_" + str(b_id) + "_rooflines.jpg")
        del sing_b_img_poly

        # write ground truth rooflines if set to true
        # sing_b_img_poly_gt = copy.deepcopy(sing_b.image)
        # if args.write_gt_building_image_with_rooflines:
        #     if args.merge_connected_building_polygons:
        #         for b_gt_id in building_polys.merged_to_original_map[i_building]:
        #             if b_gt_id in building_polys.building_gt_rooflines_dict:
        #                 for b_gt_poly in building_polys.building_gt_rooflines_dict[b_gt_id]:
        #                     b_gt_poly.convert_from_geo_to_pix(top_left_used, sing_b.pix_size, sing_b.bbox_pix)
        #                     b_gt_poly.draw_polygon(sing_b_img_poly_gt, 1)
        #     else:
        #         if b_id in building_polys.building_gt_rooflines_dict:
        #             for b_gt_poly in building_polys.building_gt_rooflines_dict[b_id]:
        #                 b_gt_poly.convert_from_geo_to_pix(top_left_used, sing_b.pix_size, sing_b.bbox_pix)
        #                 b_gt_poly.draw_polygon(sing_b_img_poly_gt, 1)
        #     sing_b.write_image(sing_b_img_poly_gt,
        #                        output_img_gt_rooflines_dir + image_name_used + "_" + str(b_id) + "_rooflines_gt.jpg")
        # del sing_b_img_poly_gt

        # write lines to gpkg
        # initialize the polygons to write if there is predict data
        rooflines_out = cd.WPolygons()
        rooflines_out_path = ROOFLINES_OUTPUT_TMPL.format(bid=str(b_id))
        rooflines_out.initialize_gpkg_for_write(rooflines_out_path, building_polys)
        rooflines_out.add_partition_lines(b_id, sing_b, used_shapes)
        rooflines_out.close_file(args)
        n_edges = len(sing_b.edges)

        # write config to 
        # with open(BUILDING_CFG_TMPL.format(bid=str(b_id)), 'a') as cfg_file:
        #     cfg_file.write("\nINPUT_ROOFLINES = '{}.gpkg'".format(rooflines_out_path))
        del sing_b.image
        del sing_b.pix_points
        del sing_b.edges
        del sing_b
        del img_used
        del top_left_used
        del image_name_used
        del which_case
        del img_path_read

        return n_edges

    # configuration parameters
    class args:
        building_id = BLD_ID
        layer_name = "geom"
        building_buffer_dis = 1.0
        layer_filter = "pc_source='DIM'"
        merge_connected_building_polygons = False
        write_gt_building_image_with_rooflines = False
        write_building_image = False
        tif_with_tfw = False
        polygon_buffer = 60
        pixel_offset = 100
        apply_polygon_buffer_filter = True
        write_gt_building_image_with_footprints = 0
        # kinetic partition
        lsd_scale = 0.8
        num_intersection = 1
        enable_regularise = True
        verbose = False

    args.verbose = verbose

    # scan dir with ortho images
    ortho_images_in = glob.glob(ORTHO_IMG_DIR + "*.tif")
    ortho_image_list, file_name_list = read_ortho_photos(ortho_images_in, ORTHO_IMG_DIR, args)

    # read building footprints
    building_polys = cd.WPolygons()
    building_polys.read_poly(building_index_file, args)

    i_building = 0
    
    n_building_files = len(building_polys.building_polygon_dict.items())
    # Loop all building polygons to crop image
    for b_id, b_poly in building_polys.building_polygon_dict.items():
        n_edges = extract_rooflines(args, b_id, b_poly, i_building, n_building_files, ortho_image_list, building_polys, file_name_list)
        i_building += 1
        logging.debug(f"Extracted rooflines for bid='{b_id}' n_edges={n_edges}")
   
    # NB this does not work, code is not thread safe
    # with ThreadPoolExecutor(max_workers=max_workers) as executor:
    #     futures = {executor.submit(extract_rooflines, args, b_id, b_poly, i_building, n_building_files, ortho_image_list, building_polys, file_name_list): b_id for b_id, b_poly in building_polys.building_polygon_dict.items()}

    #     for future in as_completed(futures):
    #         b_id = futures[future]
    #         logging.info(f"Extracted rooflines for bid='{b_id}' skipped={future.result()}")

    building_polys.close_file(args)
    del building_polys

# 3 Run gf reconstruction
def run_reconstruct(building_index_file, max_workers, skip_ortholines, config_data=None, verbose=False):
    def get_buildings(building_index_file):
        buildings = list()
        with fiona.open(building_index_file) as buildings:
            buildings = [bld for bld in buildings]
        return buildings
    def run_geoflow(building, skip_ortholines, config_data, verbose):
        def format_parameters(parameters, args):
            for (key, val) in parameters.items():
                if isinstance(val, bool):
                    if val:
                        args.append(f"--{key}=true")
                    else:
                        args.append(f"--{key}=false")
                else:
                    args.append(f"--{key}={val}")

        args = [EXE_GEOF]
        bid = str(building.properties[BLD_ID])
        if building.properties["pc_source"] == "DIM" and not skip_ortholines:
            args.append(GF_FLOWCHART_DIM)
        else:
            args.append(GF_FLOWCHART_LIDAR)
        args += ["-c", BUILDING_CFG_TMPL.format(bid=bid)]

        if verbose:
            args += ["--verbose"]
       
        if building.properties["pc_source"] == "DIM":
            args.append(f"--INPUT_ROOFLINES={ROOFLINES_OUTPUT_TMPL.format(bid=bid)}.gpkg")
            format_parameters(config_data['output']['reconstruction_parameters_dim'], args)
        else:
            format_parameters(config_data['output']['reconstruction_parameters_lidar'], args)
        
        return subprocess.run(args)
    
    buildings = get_buildings(building_index_file)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(run_geoflow, building, skip_ortholines, config_data, verbose): building for building in buildings}

        for future in as_completed(futures):
            # command = futures[future]
            result = future.result()
            if result.returncode != 0:
                logging.warning("Error occurred while executing command '{}'".format(" ".join(result.args)))

# 5 merge cjdb?
def run_tile_merge(output_city_json_path):
    # cmd = f"(cat {METADATA_NL_PATH} ; echo ; find {CJSONL_PATH} -name '*.city.jsonl' -exec cat {{}} \;  -exec echo \;) | cjio stdin save {output_city_json_path}"
    args = ["geof", GF_FLOWCHART_MERGE_FEATURES] 
    args.append(f"--path_features_input_file=/data/tmp/features.txt") 
    args.append(f"--path_metadata={METADATA_NL_PATH}") 
    args.append(f"--output_file={output_city_json_path}")
    # if verbose:
    #     args += ["--verbose"]
    result = subprocess.run(args)
    if result.returncode != 0:
        logging.warning("Error occurred while executing command '{}'".format(" ".join(result.args)))


@click.group(invoke_without_command=True)
@click.pass_context
@click.option('-c', '--config', type=click.Path(exists=True), help='Main configuration file')
@click.option('-l', '--loglevel', type=click.Choice(['INFO', 'WARNING', 'DEBUG'], case_sensitive=False), help='Print debug information')
@click.option('-j', '--jobs', default=None, type=int, help='Number of parallel jobs to use. Default is all cores.')
@click.option('--keep-tmp-data', is_flag=True, default=False, help='Do not remove temporary files (could be helpful for debugging)')
@click.option('--only-reconstruct', is_flag=True, default=False, help='Only perform the building reconstruction and tile generation steps (needs tmp data from previous run)')
@click.option('--output-tile', type=click.Path(), default="/data/output/tile", show_default=True, help='Export output tile file stem (CityJSON, GPKG formats). NB. does not include file extension.')
def cli(ctx, config, loglevel, jobs, keep_tmp_data, only_reconstruct, output_tile):
    loglvl = logging.WARNING
    if loglevel == 'INFO':
        loglvl = logging.INFO
    elif loglevel == 'WARNING':
        loglvl = logging.WARNING
    elif loglevel == 'DEBUG':
        loglvl = logging.DEBUG
    logging.basicConfig(format='%(asctime)s [%(levelname)s]: %(message)s', level=loglvl)
    if ctx.invoked_subcommand: return

    config_data = read_toml_config(config)
    indexfile = config_data['output']['index_file']
    path = config_data['output']['path']
    building_index_path = indexfile.format(path=path)

    skip_ortholines = False
    for pc in config_data['input']['pointclouds']:
        if pc["name"] == "DIM":
            if 'force_low_lod' in pc:
                skip_ortholines = pc['force_low_lod']
    # output_city_json_path = "/data/output/tile.city.json"

    logging.info(f"Config read from {config}")

    if not only_reconstruct:
        logging.info("Pointcloud selection and cropping...")
        run_crop(config, loglvl <= logging.DEBUG)
        
        if not skip_ortholines:
            logging.info("Roofline extraction from true orthophotos...")
            run_ortho_rooflines(building_index_path, jobs, loglvl <= logging.DEBUG)

    logging.info("Building reconstruction...")
    run_reconstruct(building_index_path, jobs, skip_ortholines, config_data, loglvl <= logging.DEBUG)

    if output_tile:
        logging.info("Generating CityJSON file...")
        run_tile_merge(output_tile)

    if not keep_tmp_data:
        logging.info("Cleaning up temporary files...")
        for item in os.listdir("/data/tmp"):
            item_path = os.path.join("/data/tmp", item)
            if os.path.isfile(item_path) or os.path.islink(item_path):
                os.unlink(item_path)
            elif os.path.isdir(item_path):
                shutil.rmtree(item_path)

@cli.command(help="Run a command (for debugging)")
@click.argument("commandline")
# @click.option("--commandline")
def cmd(commandline):
    args = commandline.split()
    logging.info(f"Running: {commandline}")
    result = subprocess.run(args)
    if result.returncode != 0:
        logging.warning("Error occurred while executing command '{}'".format(" ".join(result.args)))

if __name__ == '__main__':
    cli()
