# -*- coding: utf-8 -*-
"""
Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files
"""
from __future__ import division
from builtins import map, object
from past.builtins import basestring
import os
import io, codecs
import gzip
import logging
from collections import defaultdict, Counter

from qgis.core import *
import qgis.utils

qgis.utils.uninstallErrorHook()
qgis_utils = getattr(qgis.utils, 'QGis', getattr(qgis.utils, 'Qgis', None))
from osgeo import gdal

from catatom2osm import config, catatom, csvtools, layer, osm, osmxml, overpass
from catatom2osm import cdau  # Used in get_auxiliary_addresses
from catatom2osm.report import instance as report

log = config.log
if config.silence_gdal:
    gdal.PushErrorHandler('CPLQuietErrorHandler')


class QgsSingleton(QgsApplication):
    """Keeps a unique instance of QGIS for the application (and tests)"""
    _qgs = None

    def __new__(cls):
        if QgsSingleton._qgs is None:
            # Init qGis API
            QgsSingleton._qgs = QgsApplication([], False)
            qgis_prefix = os.getenv('QGISHOME')
            if qgis_prefix:
                QgsApplication.setPrefixPath(qgis_prefix, True)
            QgsApplication.initQgis()
            # sets GDAL to convert xlink references to fields but not resolve
            gdal.SetConfigOption('GML_ATTRIBUTES_TO_OGR_FIELDS', 'YES')
            gdal.SetConfigOption('GML_SKIP_RESOLVE_ELEMS', 'ALL')
        return QgsSingleton._qgs


class CatAtom2Osm(object):
    """
    Main application class for a tool to convert the data sets from the
    Spanish Cadastre ATOM Services to OSM files.
    """

    def __init__(self, a_path, options):
        """
        Constructor.

        Args:
            a_path (str): Directory where the source files are located.
            options (dict): Dictionary of options.
        """
        self.options = options
        self.cat = catatom.Reader(a_path)
        self.path = self.cat.path
        self.label = options.zone
        report.mun_code = self.cat.zip_code
        report.sys_info = True
        self.qgs = QgsSingleton()
        if report.sys_info:
            report.qgs_version = qgis_utils.QGIS_VERSION
            report.gdal_version = gdal.__version__
            log.debug(_("Initialized QGIS %s API"), report.qgs_version)
            log.debug(_("Using GDAL %s"), report.gdal_version)
        if qgis_utils.QGIS_VERSION_INT < config.MIN_QGIS_VERSION_INT:
            msg = _(
                "Required QGIS version %s or greater") % config.MIN_QGIS_VERSION
            raise ValueError(msg)
        gdal_version_int = int('{:02d}{:02d}{:02d}'.format(
            *list(map(int, gdal.__version__.split('.')))))
        if gdal_version_int < config.MIN_GDAL_VERSION_INT:
            msg = _(
                "Required GDAL version %s or greater") % config.MIN_GDAL_VERSION
            raise ValueError(msg)
        self.highway_names_path = self.get_path('highway_names.csv')
        self.tasks_path = self.get_path('tasks')
        if self.label or self.options.tasks:
            if not os.path.exists(self.tasks_path):
                os.makedirs(self.tasks_path)
        if self.label:
            self.highway_names_path = self.get_path(
                'tasks', self.label + '_highway_names.csv'
            )
            self.delete_current_osm_files()
        self.is_new = not os.path.exists(self.highway_names_path)

    def run(self):
        """Launches the app"""
        if self.options.list_zones:
            self.list_zones()
            return
        elif self.options.comment:
            self.add_comments()
            return
        log.info(_("Start processing '%s'"), report.mun_code)
        self.get_zoning()
        if not self.label:
            self.process_zoning()
        self.address_osm = osm.Osm()
        self.building_osm = osm.Osm()
        if self.options.address and self.is_new and not self.label:
            self.options.tasks = False
            self.options.building = False
            self.options.zoning = False
            self.options.parcel = False
        if self.options.building or self.options.tasks:
            self.get_building()
            if self.building.featureCount() == 0:
                return
        if self.options.address:
            self.read_address()
            if self.label or (
                not self.is_new and not self.options.manual
            ):
                current_address = self.get_current_ad_osm()
                self.address.conflate(current_address)
        if self.options.building or self.options.tasks:
            self.process_building()
            report.building_counter = Counter()
        if self.options.address:
            self.address.reproject()
            self.address_osm = self.address.to_osm()
            del self.address
            self.delete_shp('address.shp')
        if self.options.tasks:
            self.process_tasks(self.building)
        if self.options.zoning:
            self.output_zoning()
        if self.options.building:
            self.output_building()
        elif self.options.tasks:
            del self.building
            self.delete_shp('building.shp')
        if self.options.address:
            if not self.options.building and not self.options.tasks:
                report.address_stats(self.address_osm)
            if not self.label:
                self.write_osm(self.address_osm, 'address.osm')
            del self.address_osm
        if self.options.parcel:
            self.process_parcel()
        if self.label:
            self.delete_current_osm_files()
        self.end_messages()

    def list_zones(self):
        zoning_gml = self.cat.read("cadastralzoning")
        labels = {
            layer.ZoningLayer.format_label(feat)
            for feat in zoning_gml.getFeatures()
        }
        for label in sorted(labels):
            print(label)

    def add_comments(self):
        """Recover missing task files metadata after Josm editing."""
        report.from_file(self.get_path('report.txt'))
        for fn in os.listdir(self.tasks_path):
            if fn.endswith('.osm') or fn.endswith('.osm.gz'):
                label = os.path.basename(fn).split('.')[0]
                data = self.read_osm('tasks', fn)
                fixmes = sum([1 for e in data.elements if 'fixme' in e.tags])
                if fixmes > 0:
                    log.warning(_("Check %d fixme tags"), fixmes)
                oldtags = dict(data.tags)
                data.tags.update(config.changeset_tags)
                comment = ' '.join((config.changeset_tags['comment'],
                                    report.mun_code, report.mun_name, label))
                data.tags['comment'] = comment
                data.tags['generator'] = report.app_version
                if 'building_date' in report.values:
                    data.tags['source:date'] = report.building_date
                if 'address_date' in report.values:
                    data.tags['source:date:addr'] = report.address_date
                if data.tags != oldtags:
                    self.write_osm(data, 'tasks', fn)


    def zone_query(self, feat, kwargs):
        """Filter feat by zone label if needed."""
        return self.label is None or self.building.get_label(feat) == self.label

    def get_path(self, *paths):
        """Get path from components relative to self.path"""
        return os.path.join(self.path, *paths)

    def get_building(self):
        """Merge building, parts and pools"""
        building_gml = self.cat.read("building")
        report.building_date = building_gml.source_date
        fn = self.get_path('building.shp')
        layer.ConsLayer.create_shp(fn, building_gml.crs())
        self.building = layer.ConsLayer(
            fn, providerLib='ogr', source_date=building_gml.source_date
        )
        if self.options.tasks or self.label:
            self.building.get_labels(
                building_gml, self.urban_zoning, self.rustic_zoning
            )
        self.building.append(building_gml, query=self.zone_query)
        report.inp_buildings = self.building.featureCount()
        del building_gml
        part_gml = self.cat.read("buildingpart")
        if self.options.tasks or self.label:
            self.building.get_labels(
                part_gml, self.urban_zoning, self.rustic_zoning
            )
        self.building.append(part_gml, query=self.zone_query)
        self.building.detect_missing_building_parts()
        report.inp_parts = self.building.featureCount() - report.inp_buildings
        del part_gml
        other_gml = self.cat.read("otherconstruction", True)
        report.inp_pools = 0
        if other_gml:
            if self.options.tasks or self.label:
                self.building.get_labels(
                    other_gml, self.urban_zoning, self.rustic_zoning
                )
            self.building.append(other_gml, query=self.zone_query)
            report.inp_pools = (
                self.building.featureCount()
                - report.inp_buildings
                - report.inp_parts
            )
        csvtools.dict2csv(self.building.labels_path, self.building.labels)
        report.inp_features = self.building.featureCount()

    def process_tasks(self, source):
        """
        Convert shp to osm for each task.
        Remove zones without buildings (empty tasks).
        """
        self.get_tasks(source)
        zoning = [] if report.tasks_m == 0 else [('missing', None)]
        zoning += [
            (self.rustic_zoning.format_label(zone), zone.id())
            for zone in self.rustic_zoning.getFeatures()
        ]
        zoning += [
            (self.urban_zoning.format_label(zone), zone.id())
            for zone in self.urban_zoning.getFeatures()
        ]
        to_clean = {'r': [], 'u': []}
        for zone in zoning:
            label = zone[0]
            comment = ' '.join((config.changeset_tags['comment'],
                                report.mun_code, report.mun_name, label))
            fn = self.get_path('tasks', label + '.shp')
            if os.path.exists(fn):
                task = layer.ConsLayer(fn, label, 'ogr',
                                       source_date=source.source_date)
                if task.featureCount() > 0:
                    task_osm = task.to_osm(upload='yes',
                                           tags={'comment': comment})
                    del task
                    self.delete_shp(fn, False)
                    self.merge_address(task_osm, self.address_osm)
                    report.address_stats(task_osm)
                    report.cons_stats(task_osm, label)
                    self.write_osm(task_osm, 'tasks', label + '.osm.gz')
                    report.osm_stats(task_osm)
            else:
                t = 'r' if len(label) == 3 else 'u'
                to_clean[t].append(zone[1])
        if to_clean['r']:
            self.rustic_zoning.writer.deleteFeatures(to_clean['r'])
        if to_clean['u']:
            self.urban_zoning.writer.deleteFeatures(to_clean['u'])

    def get_tasks(self, source):
        """
        Put each building into a shp file named according to the field 'label'.
        """
        if os.path.exists(self.tasks_path):
            for fn in os.listdir(self.tasks_path):
                os.remove(os.path.join(self.tasks_path, fn))
        tasks_r = 0
        tasks_u = 0
        tasks_m = 0
        last_task = None
        to_add = []
        fcount = source.featureCount()
        for i, feat in enumerate(source.getFeatures()):
            label = feat['task'] or ''
            f = source.copy_feature(feat, {}, {})
            if i == fcount - 1 or last_task is None or label == last_task:
                to_add.append(f)
            if i == fcount - 1 or (
                last_task is not None and label != last_task
            ):
                if last_task == '':
                    last_task = 'missing'
                    tasks_m += len(to_add)
                fn = os.path.join(self.tasks_path, last_task + '.shp')
                if not os.path.exists(fn):
                    layer.ConsLayer.create_shp(fn, source.crs())
                    if len(last_task or '') == 3:
                        tasks_r += 1
                    elif len(last_task or '') == 5:
                        tasks_u += 1
                task = layer.ConsLayer(
                    fn, last_task, 'ogr', source_date=source.source_date
                )
                task.writer.addFeatures(to_add)
                to_add = [f]
            last_task = label
        log.debug(_("Generated %d rustic and %d urban tasks files"), tasks_r,
                  tasks_u)
        if tasks_m > 0:
            msg = _(
                "There are %d buildings without zone, check tasks/missing.osm"
            ) % tasks_m
            log.warning(msg)
            report.warnings.append(msg)
        report.tasks_r = tasks_r
        report.tasks_u = tasks_u
        report.tasks_m = tasks_m

    def process_zoning(self):
        self.rustic_zoning.clean()
        self.rustic_zoning.set_tasks(self.cat.zip_code)
        if self.urban_zoning.featureCount() > 0:
            self.urban_zoning.topology()
            self.urban_zoning.delete_invalid_geometries()
            self.urban_zoning.simplify()
            self.urban_zoning.set_tasks(self.cat.zip_code)
            self.rustic_zoning.difference(self.urban_zoning)

    def output_zoning(self):
        self.urban_zoning.reproject()
        self.rustic_zoning.reproject()
        out_path = self.get_path('boundary.poly')
        self.rustic_zoning.export_poly(out_path)
        log.info(_("Generated '%s'"), out_path)
        self.export_layer(self.urban_zoning, 'urban_zoning.geojson',
                          'GeoJSON')
        self.export_layer(self.rustic_zoning, 'rustic_zoning.geojson',
                          'GeoJSON')
        self.rustic_zoning.append(self.urban_zoning)
        self.export_layer(self.rustic_zoning, 'zoning.geojson', 'GeoJSON')
        if hasattr(self, 'urban_zoning'):
            del self.urban_zoning
            self.delete_shp('urban_zoning.shp')
        if hasattr(self, 'rustic_zoning'):
            del self.rustic_zoning
        self.delete_shp('rustic_zoning.shp')

    def process_building(self):
        """Process all buildings dataset"""
        self.building.remove_outside_parts()
        self.building.explode_multi_parts()
        self.building.clean()
        self.building.validate(report.max_level, report.min_level)
        if self.options.address:
            self.building.move_address(self.address)
        self.building.reproject()
        if self.options.tasks:
            self.building.set_tasks(self.urban_zoning, self.rustic_zoning)
        if not self.options.manual:
            current_bu_osm = self.get_current_bu_osm()
            if self.building.conflate(current_bu_osm):
                self.write_osm(current_bu_osm, 'current_building.osm')
            del current_bu_osm

    def output_building(self):
        self.building_osm = self.building.to_osm()
        del self.building
        self.delete_shp('building.shp')
        if self.options.address:
            self.merge_address(self.building_osm, self.address_osm)
            if not self.options.tasks:
                report.address_stats(self.building_osm)
        if not self.options.tasks:
            report.cons_stats(self.building_osm)
        if self.label is None:
            self.write_osm(self.building_osm, 'building.osm')
        else:
            if not os.path.exists(self.tasks_path):
                os.makedirs(self.tasks_path)
            self.write_osm(self.building_osm, 'tasks', self.label + '.osm.gz')
        if not self.options.tasks:
            report.osm_stats(self.building_osm)
        del self.building_osm

    def process_parcel(self):
        parcel_gml = self.cat.read("cadastralparcel")
        fn = self.get_path('parcel.shp')
        layer.ParcelLayer.create_shp(fn, parcel_gml.crs())
        parcel = layer.ParcelLayer(fn, providerLib='ogr',
                                   source_date=parcel_gml.source_date)
        parcel.append(parcel_gml)
        del parcel_gml
        parcel.reproject()
        parcel_osm = parcel.to_osm()
        del parcel
        self.delete_shp('parcel.shp')
        self.write_osm(parcel_osm, "parcel.osm")

    def end_messages(self):
        if report.fixme_stats():
            log.warning(_("Check %d fixme tags"), report.fixme_count)
        if self.options.tasks:
            filename = 'review.txt'
            with open(self.get_path(filename), "w") as fo:
                fo.write(
                    config.eol.join(report.get_tasks_with_fixmes()) + config.eol)
                log.info(
                    _("Generated '%s'") + '. ' + _("Please, check it"), filename
                )
        if self.options.tasks or self.options.building:
            report.cons_end_stats()
        if self.options.tasks or self.options.building or self.options.address:
            report.to_file(self.get_path('report.txt'))
        if self.is_new:
            msg = (
                _("Generated '%s'") + '. ' + _("Please, check it and run again")
            )
            log.info(msg, self.highway_names_path)
        else:
            log.info(_("Finished!"))

    def exit(self):
        """Ends properly"""
        for propname in list(self.__dict__.keys()):
            if isinstance(getattr(self, propname), QgsVectorLayer):
                delattr(self, propname)
        if hasattr(self, 'qgs'):
            self.qgs.exitQgis()

    def export_layer(self, layer, filename, driver_name='ESRI Shapefile',
                     target_crs_id=None):
        """
        Export a vector layer.

        Args:
            layer (QgsVectorLayer): Source layer.
            filename (str): Output filename.
            driver_name (str): Defaults to ESRI Shapefile.
            target_crs_id (int): Defaults to source CRS.
        """
        out_path = self.get_path(filename)
        if layer.export(out_path, driver_name, target_crs_id=target_crs_id):
            log.info(_("Generated '%s'"), filename)
        else:
            raise IOError(_("Failed to write layer: '%s'") % filename)

    def read_osm(self, *paths, **kwargs):
        """
        Reads a OSM data set from a OSM XML file. If the file not exists,
        downloads data from overpass using ql query

        Args:
            paths (str): input filename components relative to self.path
            ql (str): Query to put in the url for overpass

        Returns
            Osm: OSM data set
        """
        ql = kwargs.get('ql', False)
        osm_path = self.get_path(*paths)
        filename = os.path.basename(osm_path)
        if not os.path.exists(osm_path):
            if not ql:
                return None
            log.info(_("Downloading '%s'") % filename)
            query = overpass.Query(self.cat.boundary_search_area).add(ql)
            if log.getEffectiveLevel() == logging.DEBUG:
                query.download(osm_path, log)
            else:
                query.download(osm_path)
        if osm_path.endswith('.gz'):
            fo = gzip.open(osm_path, 'rb')
        else:
            fo = open(osm_path, 'rb')
        data = osmxml.deserialize(fo)
        if len(data.elements) == 0:
            msg = _("No OSM data were obtained from '%s'") % filename
            log.warning(msg)
            report.warnings.append(msg)
        else:
            log.info(_("Read '%s': %d nodes, %d ways, %d relations"),
                     filename, len(data.nodes), len(data.ways),
                     len(data.relations))
        return data

    def write_osm(self, data, *paths):
        """
        Generates a OSM XML file for a OSM data set.

        Args:
            data (Osm): OSM data set
            paths (str): output filename components relative to self.path
                            (compress if ends with .gz)
        """
        for e in data.elements:
            if 'ref' in e.tags:
                del e.tags['ref']
        data.merge_duplicated()
        osm_path = self.get_path(*paths)
        if osm_path.endswith('.gz'):
            file_obj = codecs.getwriter("utf-8")(gzip.open(osm_path, "w"))
        else:
            file_obj = io.open(osm_path, "w", encoding="utf-8")
        osmxml.serialize(file_obj, data)
        file_obj.close()
        log.info(_("Generated '%s': %d nodes, %d ways, %d relations"),
                 os.path.basename(osm_path), len(data.nodes), len(data.ways),
                 len(data.relations))

    def get_zoning(self):
        """
        Reads cadastralzoning and splits in 'MANZANA' (urban) and 'POLIGONO'
        (rustic)
        """
        zoning_gml = self.cat.read("cadastralzoning")
        fn = self.get_path('rustic_zoning.shp')
        layer.ZoningLayer.create_shp(fn, zoning_gml.crs())
        self.rustic_zoning = layer.ZoningLayer(fn, 'rusticzoning', 'ogr')
        fn = self.get_path('urban_zoning.shp')
        layer.ZoningLayer.create_shp(fn, zoning_gml.crs())
        self.urban_zoning = layer.ZoningLayer(fn, 'urbanzoning', 'ogr')
        self.rustic_zoning.append(zoning_gml, level='P')
        if self.options.tasks or self.options.zoning or self.label:
            self.urban_zoning.append(zoning_gml, level='M')
        if self.label:
            self.cat.boundary_search_area = zoning_gml.bounding_box(
                "label = '%s'" % self.label
            )
        else:
            self.cat.get_boundary(self.rustic_zoning)
            report.mun_area = round(self.rustic_zoning.get_area() / 1E6, 1)
        del zoning_gml
        report.cat_mun = self.cat.cat_mun
        report.mun_name = getattr(self.cat, 'boundary_name', None)
        if hasattr(self.cat, 'boundary_data'):
            if 'wikipedia' in self.cat.boundary_data:
                report.mun_wikipedia = self.cat.boundary_data['wikipedia']
            if 'wikidata' in self.cat.boundary_data:
                report.mun_wikidata = self.cat.boundary_data['wikidata']
            if 'population' in self.cat.boundary_data:
                report.mun_population = (self.cat.boundary_data['population'],
                                         self.cat.boundary_data.get(
                                             'population:date', '?'))

    def read_address(self):
        """Reads Address GML dataset"""
        address_gml = self.cat.read("address")
        report.address_date = address_gml.source_date
        if address_gml.writer.fieldNameIndex('component_href') == -1:
            address_gml = self.cat.read("address", force_zip=True)
            if address_gml.writer.fieldNameIndex('component_href') == -1:
                msg = _("Could not resolve joined tables for the "
                        "'%s' layer") % address_gml.name()
                raise IOError(msg)
        postaldescriptor = self.cat.read("postaldescriptor")
        thoroughfarename = self.cat.read("thoroughfarename")
        report.inp_address = address_gml.featureCount()
        report.inp_zip_codes = postaldescriptor.featureCount()
        report.inp_street_names = thoroughfarename.featureCount()
        report.inp_address_entrance = address_gml.count(
            "specification='Entrance'")
        report.inp_address_parcel = address_gml.count("specification='Parcel'")
        fn = self.get_path('address.shp')
        layer.AddressLayer.create_shp(fn, address_gml.crs())
        self.address = layer.AddressLayer(fn, providerLib='ogr',
                                          source_date=address_gml.source_date)
        self.address.append(address_gml, query=self.zone_query)
        self.address.join_field(postaldescriptor, 'PD_id', 'gml_id',
                                ['postCode'])
        self.address.join_field(thoroughfarename, 'TN_id', 'gml_id', ['text'],
                                'TN_')
        self.get_auxiliary_addresses()
        self.address.get_image_links()
        self.export_layer(self.address, 'address.geojson', 'GeoJSON',
                          target_crs_id=4326)
        highway_names = self.get_translations(self.address)
        ia = self.address.translate_field('TN_text', highway_names)
        if ia > 0:
            log.debug(_("Deleted %d addresses refused by street name"), ia)
            report.values['ignored_addresses'] = ia

    def get_auxiliary_addresses(self):
        """If exists, reads and conflate an auxiliary addresses data source"""
        for source in list(config.aux_address.keys()):
            if self.cat.zip_code[:2] in config.aux_address[source]:
                aux_source = globals()[source]
                aux_path = os.path.join(
                    os.path.dirname(self.path), config.aux_path
                )
                reader = aux_source.Reader(aux_path)
                aux = reader.read(self.cat.zip_code[:2])
                aux_source.conflate(aux, self.address, self.cat.zip_code)

    def merge_address(self, building_osm, address_osm):
        """
        Copy address from address_osm to building_osm using 'ref' tag.

        If there exists one building with the same 'ref' that an address, copy
        the address tags to the building if it isn't a 'entrace' type address or
        else to the entrance if there exist a node with the address coordinates
        in the building.

        Precondition: building.move_address deleted addresses belonging to multiple buildings

        Args:
            building_osm (Osm): OSM data set with buildings
            address_osm (Osm): OSM data set with addresses
        """
        if 'source:date' in address_osm.tags:
            building_osm.tags['source:date:addr'] = address_osm.tags[
                'source:date']
        address_index = defaultdict(list)
        building_index = defaultdict(list)
        for bu in building_osm.elements:
            if 'ref' in bu.tags:
                building_index[bu.tags['ref']].append(bu)
        for ad in address_osm.nodes:
            if ad.tags['ref'] in building_index:
                address_index[ad.tags['ref']].append(ad)
        md = 0
        for (ref, group) in list(building_index.items()):
            address_count = len(address_index[ref])
            if address_count == 0:
                continue
            entrance_count = sum([1 if 'entrance' in ad.tags else 0
                                  for ad in address_index[ref]])
            parcel_count = address_count - entrance_count
            if parcel_count > 1 or (parcel_count == 1 and entrance_count > 0):
                md += address_count
                continue
            for ad in address_index[ref]:
                bu = group[0]
                entrance = False
                if 'entrance' in ad.tags:
                    outline = [bu] if isinstance(bu, osm.Way) \
                        else [m.element for m in bu.members if
                              m.role == 'outer']
                    for w in outline:
                        entrance = w.search_node(ad.x, ad.y)
                        if entrance:
                            entrance.tags.update(ad.tags)
                            entrance.tags.pop('ref', None)
                            entrance.tags.pop('image', None)
                            break
                if not entrance:
                    bu.tags.update(ad.tags)
                    bu.tags.pop('image', None)
        if md > 0:
            log.debug(
                _("Refused %d 'parcel' addresses not unique for it building"),
                md)
            report.inc('not_unique_addresses', md)

    def get_translations(self, address):
        """
        If there exists the configuration file 'highway_types.csv', read it,
        else write one with default values. If don't exists the translations file
        'highway_names.csv', creates one parsing current OSM highways data, else
        reads and returns it as a dictionary.

        * 'highway_types.csv' List of osm elements in json format located in the
          application path that contains translations from abbreviations to full
          types of highways.

        * 'highway_names.csv' is located in the outputh folder and contains
          corrections for original highway names.
        """
        highway_types_path = os.path.join(config.app_path, 'highway_types.csv')
        if not os.path.exists(highway_types_path):
            csvtools.dict2csv(highway_types_path, config.highway_types)
        else:
            csvtools.csv2dict(highway_types_path, config.highway_types)
        if self.is_new:
            if self.options.manual:
                highway = None
            else:
                highway = self.get_highway()
                highway.reproject(address.crs())
            highway_names = address.get_highway_names(highway)
            csvtools.dict2csv(self.highway_names_path, highway_names, sort=1)
        else:
            highway_names = csvtools.csv2dict(self.highway_names_path, {})
        for key, value in list(highway_names.items()):
            highway_names[key] = value.strip()
        return highway_names

    def get_highway(self):
        """Gets OSM highways needed for street names conflation"""
        ql = ['way["highway"]["name"]',
              'relation["highway"]["name"]',
              'way["place"="square"]["name"]',
              'relation["place"="square"]["name"]']
        highway_osm = self.read_osm('current_highway.osm', ql=ql)
        highway = layer.HighwayLayer()
        highway.read_from_osm(highway_osm)
        del highway_osm
        return highway

    def get_current_ad_osm(self):
        """Gets OSM address for address conflation"""
        ql = ['node["addr:street"]["addr:housenumber"]',
              'way["addr:street"]["addr:housenumber"]',
              'relation["addr:street"]["addr:housenumber"]',
              'node["addr:place"]["addr:housenumber"]',
              'way["addr:place"]["addr:housenumber"]',
              'relation["addr:place"]["addr:housenumber"]']
        address_osm = self.read_osm('current_address.osm', ql=ql)
        current_address = set()
        w = 0
        report.osm_addresses = 0
        for d in address_osm.elements:
            if 'addr:housenumber' not in d.tags:
                if 'addr:street' in d.tags or 'addr:place' in d.tags:
                    w += 1
            elif 'addr:street' in d.tags:
                current_address.add(
                    d.tags['addr:street'] + d.tags['addr:housenumber'])
                report.osm_addresses += 1
            elif 'addr:place' in d.tags:
                current_address.add(
                    d.tags['addr:place'] + d.tags['addr:housenumber'])
                report.osm_addresses += 1
        if w > 0:
            msg = _(
                "There are %d address without house number in the OSM data") % w
            log.warning(msg)
            report.warnings.append(msg)
            report.osm_addresses_whithout_number = w
        return current_address

    def get_current_bu_osm(self):
        """Gets OSM buildings for building conflation"""
        ql = 'way[building];relation[building];way[leisure=swimming_pool];relation[leisure=swimming_pool]'
        current_bu_osm = self.read_osm('current_building.osm', ql=ql)
        return current_bu_osm

    def delete_shp(self, name, relative=True):
        if log.getEffectiveLevel() > logging.DEBUG:
            path = self.get_path(name) if relative else name
            layer.BaseLayer.delete_shp(path)

    def delete_current_osm_files(self):
        if log.getEffectiveLevel() == logging.DEBUG:
            return
        for f in ['current_address', 'current_building', 'current_highway']:
            fn = self.get_path(f + '.osm')
            if os.path.exists(fn):
                os.remove(fn)
