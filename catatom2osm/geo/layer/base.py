import logging
import os
import re
from tqdm import tqdm

from qgis.core import (
    QgsCoordinateReferenceSystem, QgsCoordinateTransform, QgsExpression,
    QgsFeature, QgsFeatureRequest, QgsFields, QgsGeometry, QgsProject,
    QgsSpatialIndex, QgsVectorLayer, QgsVectorFileWriter,
)

from catatom2osm import config, osm, translate
from catatom2osm.geo import BUFFER_SIZE
from catatom2osm.geo.geometry import Geometry
from catatom2osm.geo.point import Point
from catatom2osm.geo.aux import get_attributes
from catatom2osm.geo.types import WKBPoint, WKBPolygon, WKBMultiPolygon

log = logging.getLogger(config.app_name)


class BaseLayer(QgsVectorLayer):
    """Base class for application layers"""

    def __init__(self, path, baseName, providerLib = "ogr"):
        super(BaseLayer, self).__init__(path, baseName, providerLib)
        self.writer = self.dataProvider()
        self.rename={}
        self.resolve={}
        self.reference_matchs={}
        self.keep = False

    @staticmethod
    def get_writer(name, crs, fields=QgsFields(), geom_type=WKBMultiPolygon):
        transform_context = QgsProject.instance().transformContext()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = "ESRI Shapefile"
        save_options.fileEncoding = "UTF-8"
        return QgsVectorFileWriter.create(
            name, fields, geom_type, crs, transform_context, save_options
        )

    @staticmethod
    def create_shp(name, crs, fields=QgsFields(), geom_type=WKBMultiPolygon):
        writer = BaseLayer.get_writer(name, crs, fields, geom_type)
        if writer.hasError() != QgsVectorFileWriter.NoError:
            msg = _(
                "Error when creating shapefile: '%s'"
            ) % writer.errorMessage()
            raise IOError(msg)
        return writer

    @staticmethod
    def delete_shp(path):
        QgsVectorFileWriter.deleteShapeFile(path)
        path = os.path.splitext(path)[0] + '.cpg'
        if os.path.exists(path):
            os.remove(path)

    @staticmethod
    def get_crs_transform(source_crs, target_crs):
        prj = QgsProject.instance()
        return QgsCoordinateTransform(source_crs, target_crs, prj)

    def writeAsVectorFormat(self, name, driver_name, target_crs=None):
        transform_context = QgsProject.instance().transformContext()
        save_options = QgsVectorFileWriter.SaveVectorOptions()
        save_options.driverName = driver_name
        save_options.fileEncoding = "UTF-8"
        if target_crs is not None or target_crs != self.crs():
            save_options.ct = QgsCoordinateTransform(
                self.crs(),
                QgsCoordinateReferenceSystem(target_crs),
                transform_context,
            )
        return QgsVectorFileWriter.writeAsVectorFormatV2(
            self, name, transform_context, save_options
        )

    def copy_feature(self, feature, rename=None, resolve=None):
        r"""
        Return a copy of feature renaming attributes or resolving xlink
        references.

        Args:
            feature (QgsFeature): Source feature
            rename (dict): Translation of attributes names
            resolve (dict): xlink reference fields

        Examples:
            With this:

            >>> rename = {'spec': 'specification'}
            >>> resolve = {
            ...     'PD_id': ('component_href', r'[\w\.]+PD[\.0-9]+'),
            ...     'TN_id': ('component_href', r'[\w\.]+TN[\.0-9]+'),
            ...     'AU_id': ('component_href', r'[\w\.]+AU[\.0-9]+')
            ... }

            You get:

            >>> original_attributes = ['localId', 'specification', 'component_href']
            >>> original_values = [
            ...     '38.012.1.12.0295603CS6109N',
            ...     'Parcel',
            ...     '(3:#ES.SDGC.PD.38.012.38570,#ES.SDGC.TN.38.012.1,#ES.SDGC.AU.38.012)'
            ... ]
            >>> final_attributes = ['localId', 'spec', 'PD_id', 'TN_id', 'AU_id']
            >>> final_values = [
            ...     '38.012.1.12.0295603CS6109N',
            ...     'Parcel',
            ...     'ES.SDGC.PD.38.012.38570',
            ...     'ES.SDGC.TN.38.012.1',
            ...     'ES.SDGC.AU.38.012'
            ... ]
        """
        rename = rename if rename is not None else self.rename
        resolve = resolve if resolve is not None else self.resolve
        if self.fields().isEmpty():
            self.writer.addAttributes(feature.fields().toList())
            self.updateFields()
        dst_ft = QgsFeature(self.fields())
        dst_ft.setGeometry(feature.geometry())  # TODO: Add makeValid (QGIS3)
        src_attrs = [f.name() for f in feature.fields()]
        for field in self.fields().toList():
            dst_attr = field.name()
            if dst_attr in resolve:
                (src_attr, reference_match) = resolve[dst_attr]
                src_val = feature[src_attr]
                if isinstance(src_val, (list,)):
                    src_val = ' '.join(src_val)
                match = re.search(reference_match, src_val)
                if match:
                    dst_ft[dst_attr] = match.group(0)
            else:
                src_attr = dst_attr
                if dst_attr in rename and rename[dst_attr] in src_attrs:
                    src_attr = rename[dst_attr]
                if src_attr in src_attrs:
                    dst_ft[dst_attr] = feature[src_attr]
        return dst_ft

    def append(self, layer, rename=None, resolve=None, query=None, **kwargs):
        """Copy all features from layer.

        Args:
            layer (QgsVectorLayer): Source layer
            rename (dict): Translation of attributes names
            resolve (dict): xlink reference fields
            query (func): function with args feature and kwargs that returns
                a boolean deciding if each feature will be included or not
            kwargs: aditional arguments for query function

        Examples:

            >>> query = lambda feat, kwargs: feat['foo']=='bar'
            Will copy only features with a value 'bar' in the field 'foo'.
            >>> query = lambda feat, kwargs: layer.is_inside(feat, kwargs['zone'])
            Will copy only features inside zone.

            See also copy_feature().
        """
        self.setCrs(layer.crs())
        total = 0
        to_add = []
        pbar = self.get_progressbar(_("Append"), layer.featureCount())
        for feature in layer.getFeatures():
            geom = feature.geometry()
            if not query or query(feature, kwargs):
                if (
                    geom.wkbType() == WKBPoint
                    or len(Geometry.get_multipolygon(geom))
                ) >= 1:
                    to_add.append(self.copy_feature(feature, rename, resolve))
                    total += 1
            if len(to_add) > BUFFER_SIZE:
                self.writer.addFeatures(to_add)
                to_add = []
            pbar.update()
        pbar.close()
        if len(to_add) > 0:
            self.writer.addFeatures(to_add)
        if total:
            msg = _("Loaded %d features in '%s' from '%s'")
            log.debug (msg, total, self.name(), layer.name())

    def reproject(self, target_crs=None):
        """Reproject all features in this layer to a new CRS.

        Args:
            target_crs (QgsCoordinateReferenceSystem): New CRS to apply.
        """
        if target_crs is None:
            target_crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
        crs_transform = self.get_crs_transform(self.crs(), target_crs)
        to_change = {}
        pbar = self.get_progressbar(_("Reproject"), self.featureCount())
        for feature in self.getFeatures():
            geom = QgsGeometry(feature.geometry())
            geom.transform(crs_transform)
            to_change[feature.id()] = geom
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeGeometryValues(to_change)
                to_change = {}
            pbar.update()
        pbar.close()
        if len(to_change) > 0:
            self.writer.changeGeometryValues(to_change)
        self.setCrs(target_crs)
        self.updateExtents()
        if self.writer.storageType() == 'ESRI Shapefile':
            path = self.writer.dataSourceUri().split('|')[0]
            path = os.path.splitext(path)[0]
            if os.path.exists(path + '.prj'):
                os.remove(path + '.prj')
            if os.path.exists(path + '.qpj'):
                os.remove(path + '.qpj')
        log.debug(_("Reprojected the '%s' layer to '%s' CRS"),
            self.name(), target_crs.description())

    def join_field(self, source_layer, target_field_name, join_field_name,
            field_names_subset, prefix = ""):
        """
        Replaces qgis table join mechanism becouse I'm not able to work with it
        in standalone script mode (without GUI).

        Args:
            source_layer (QgsVectorLayer): Source layer.
            target_field_name (str): Join field in the target layer.
            join_fieldsName (str): Join field in the source layer.
            field_names_subset (list): List of field name strings for the target layer.
            prefix (str): An optional prefix to add to the target fields names
        """
        fields = []
        target_attrs = [f.name() for f in self.fields()]
        for attr in field_names_subset:
            field = source_layer.fields().field(attr)
            field.setName(prefix + attr)
            if field.name() not in target_attrs:
                if field.length() > 254:
                    field.setLength(254)
                fields.append(field)
        self.writer.addAttributes(fields)
        self.updateFields()
        source_values = {}
        pbar = self.get_progressbar(
            _("Join field"), self.featureCount() + source_layer.featureCount()
        )
        for feature in source_layer.getFeatures():
            source_values[feature[join_field_name]] = {
                attr: feature[attr] for attr in field_names_subset
            }
            pbar.update()
        total = 0
        to_change = {}
        for feature in self.getFeatures():
            attrs = {}
            for attr in field_names_subset:
                fieldId = feature.fieldNameIndex(prefix + attr)
                value = None
                if feature[target_field_name] in source_values:
                    value = source_values[feature[target_field_name]][attr]
                attrs[fieldId] = value
            to_change[feature.id()] = attrs
            total += 1
            if len(to_change) > BUFFER_SIZE:
                self.writer.changeAttributeValues(to_change)
                to_change = {}
            pbar.update()
        pbar.close()
        if len(to_change) > 0:
            self.writer.changeAttributeValues(to_change)
        if total:
            log.debug(_("Joined '%s' to '%s'"), source_layer.name(),
                self.name())

    def translate_field(self, field_name, translations, clean=True):
        """
        Transform the values of a field

        Args:
            field_name (str): Name of the field to transform
            translations (dict): A dictionary used to transform field values
            clean (bool): If true (default), delete features without translation
        """
        to_clean = []
        field_ndx = self.writer.fieldNameIndex(field_name)
        if field_ndx >= 0:
            to_change = {}
            for feat in self.getFeatures():
                value = feat[field_name]
                if value in translations and translations[value] != '':
                    new_value = translations[value]
                    feat[field_name] = new_value
                    to_change[feat.id()] = get_attributes(feat)
                elif clean:
                    to_clean.append(feat.id())
            self.writer.changeAttributeValues(to_change)
        if len(to_clean):
            self.writer.deleteFeatures(to_clean)
        return len(to_clean)

    def get_index(self):
        """Returns a QgsSpatialIndex of all features in this layer (overpass
        QGIS exception for void layers)"""
        if self.featureCount() > 0:
            return QgsSpatialIndex(self.getFeatures())
        else:
            return QgsSpatialIndex()

    def bounding_box(self, expression=None):
        """Returns bounding box in overpass format of matching features using
        an expression or all features if expression is None. """
        if expression is None:
            self.selectAll()
        else:
            self.selectByExpression(expression)
        bbox = self.boundingBoxOfSelected()
        return self.get_overpass_bbox(bbox)

    def get_overpass_bbox(self, bbox):
        """
        bbox is transformed to EPSG 4326 and returns str in overpass format.
        """
        if bbox.isEmpty():
            bbox = None
        else:
            p1 = Geometry.fromPointXY(Point(bbox.xMinimum(), bbox.yMinimum()))
            p2 = Geometry.fromPointXY(Point(bbox.xMaximum(), bbox.yMaximum()))
            target_crs = QgsCoordinateReferenceSystem.fromEpsgId(4326)
            crs_transform = self.get_crs_transform(self.crs(), target_crs)
            p1.transform(crs_transform)
            p2.transform(crs_transform)
            bbox = [
                p1.asPoint().y() - config.bbox_buffer,
                p1.asPoint().x() - config.bbox_buffer,
                p2.asPoint().y() + config.bbox_buffer,
                p2.asPoint().x() + config.bbox_buffer,
            ]
            bbox = '{:.8f},{:.8f},{:.8f},{:.8f}'.format(*bbox)
        return bbox

    def export(
        self,
        path,
        driver_name="ESRI Shapefile",
        overwrite=True,
        target_crs_id=None,
    ):
        """Write layer to file

        Args:
            path (str): Path of the output file
            driver_name (str): Defaults to ESRI Shapefile.
            overwrite (bool): Defaults to True
            target_crs_id (int): Defaults to source CRS
        """
        if target_crs_id is None:
            target_crs = self.crs()
        else:
            target_crs = QgsCoordinateReferenceSystem.fromEpsgId(target_crs_id)
        if os.path.exists(path) and overwrite:
            if driver_name == 'ESRI Shapefile':
                QgsVectorFileWriter.deleteShapeFile(path)
            else:
                os.remove(path)
        result = self.writeAsVectorFormat(path, driver_name, target_crs)
        try:
            return result[0] == QgsVectorFileWriter.NoError
        except TypeError:
            return result == QgsVectorFileWriter.NoError

    def to_osm(
        self,
        tags_translation=translate.all_tags,
        data=None,
        tags={},
        upload='never',
    ):
        """
        Export this layer to an Osm data set

        Args:
            tags_translation (function): Function to translate fields to tags.
                By defaults convert all fields.
            data (Osm): OSM data set to append. By default creates a new one.
            upload (str): upload attribute of the osm dataset, default 'never'
            tags (dict): tags to update config.changeset_tags

        Returns:
            Osm: OSM data set
        """
        if data is None:
            generator = config.app_name + ' ' + config.app_version
            data = osm.Osm(upload, generator=generator)
            nodes = ways = relations = 0
        else:
            nodes = len(data.nodes)
            ways = len(data.ways)
            relations = len(data.relations)
        for feature in self.getFeatures():
            geom = feature.geometry()
            e = None
            if geom.wkbType() == WKBPoint:
                e = data.Node(geom.asPoint())
            elif geom.wkbType() in [WKBPolygon, WKBMultiPolygon]:
                mp = Geometry.get_multipolygon(geom)
                if len(mp) == 1:
                    if len(mp[0]) == 1:
                        e = data.Way(mp[0][0])
                    else:
                        e = data.Polygon(mp[0])
                else:
                    e = data.MultiPolygon(mp)
            else:
                msg = _("Detected a %s geometry in the '%s' layer") % (
                    geom.wkbType(), self.name()
                )
                log.warning(msg)
                report.warnings.append(msg)
            if e: e.tags.update(tags_translation(feature))
        changeset_tags = dict(config.changeset_tags, **tags)
        for (key, value) in changeset_tags.items():
            data.tags[key] = value
        if getattr(self, 'source_date', False):
            data.tags['source:date'] = self.source_date
        log.debug(_("Loaded %d nodes, %d ways, %d relations from '%s' layer"),
            len(data.nodes) - nodes, len(data.ways) - ways,
            len(data.relations) - relations, self.name())
        return data

    def search(self, expression=''):
        """Returns a features iterator for this search expression"""
        if expression == '':
            return self.getFeatures()
        exp = QgsExpression(expression)
        request = QgsFeatureRequest(exp)
        return self.getFeatures(request)

    def count(self, expression='', unique=''):
        """Returns number of features for this search expression"""
        count = 0
        exists = set()
        for f in self.search(expression):
            if unique:
                if f[unique] not in exists:
                    count += 1
                    exists.add(f[unique])
            else:
                count += 1
        return count

    def get_progressbar(self, description, total=None):
        """Return progress bar with 'description' for 'total' iterations"""
        leave = log.app_level <= logging.DEBUG
        pbar = tqdm(total=total, leave=leave)
        pbar.set_description(description)
        pbar.set_postfix(file=os.path.basename(self.source()), refresh=False)
        return pbar
