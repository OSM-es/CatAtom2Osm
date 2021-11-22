Léeme
=====

Herramienta para convertir los conjuntos de datos INSPIRE de los Servicios ATOM 
del Catastro Español (http://www.catastro.minhap.gob.es/webinspire/index.html) 
a archivos OSM. Esto es parte de una propuesta de importación en construcción:

https://wiki.openstreetmap.org/wiki/ES:Catastro_espa%C3%B1ol/Importaci%C3%B3n_de_edificios

Requisitos
----------

* fuzzywuzzy\[speedup\]
* psutil
* pyqgis
* requests
* GDAL

Fuzzywuzzy es necesario para la combinación de nombres de calles.
Los requisitos principales (pyqgis, GDAL) debe proporcionarlos QGIS usando los 
instaladores disponibles en http://qgis.org/

Se necestitan QGIS >= 2.10.1, GDAL >= 2.

Instalación
-----------

Se recomienda usar la herramienta mediante esta imagen de Docker 
(https://hub.docker.com/r/egofer/catatom2osm).

Si se desea una instalación sin Docker ver INSTALL.es.md (https://OSM-es.github.io/CatAtom2Osm/es/install.html) 

Uso
---

Para ejecutar la aplicación:

    catatom2osm <ruta>

El argumento ruta indica el directorio para los ficheros de entrada y salida.
El nombre del directorio debe comenzar con 5 dígitos (GGMMM) correspondientes 
al Código de Oficina Provincial del Catastro y Código de Municipio. Si el 
programa no encuentra los archivos de entrada los descargará de los Servicios 
INSPIRE del Catastro Español.

**Opciones**:

* \-h, --help                Muestra este mensaje de ayuda y termina
* \-v, --version             Imprime la versión de CatAtom2Osm y termina
* \-l [prov], --list [prov]  Lista los municipios disponibles para el código provincial de dos dígitos
* \-t, --tasks               Reparte las construcciones en archivos de tareas (predeterminada, implica -z)
* \-b, --building            Procesa los edificios a un archivo individual en lugar de tareas
* \-d, --address             Procesa el conjunto de datos de direcciones
* \-z, --zoning              Procesa el conjunto de datos de zonificación catastral
* \-p, --parcel              Procesa el conjunto de datos de parcelas catastrales
* \-a, --all                 Procesa todos los conjuntos de datos (equivalente a -bdptz)
* \-r label, --rustic label  Procesa un polígono de rústica dada su etiqueta
* \-u label, --urban label   Procesa una manzana urbana dada su etiqueta
* \-m, --manual              Desactiva la combinación con datos OSM
* \-w, --download            Solo descargar
* \--log=log_level           Selecciona el nivel de registro entre DEBUG, INFO, WARNING, ERROR o CRITICAL.

Configuración
-------------

El programa usa la configuración de localización del sistema para seleccionar el idioma en la traducción de los tipos de nombres de viales. Si quieres usar otro, asigna la variable de entorno LANG.

	LANG=es_ES.UTF-8; catatom2osm

Para forzar a usar Español.

	LANG=cat_ES.UTF-8; catatom2osm

Para forzar a usar Catalán.

	LANG=cat_ES.UTF-8; catatom2osm

Para forzar a usar Gallego.

Documentación
-------------

Consulta la documentación del programa.

https://OSM-es.github.io/CatAtom2Osm/es

