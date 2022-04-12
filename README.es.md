Léeme
=====

![](https://user-images.githubusercontent.com/1605829/141660065-1ad64b8f-dde9-4946-a4af-b556c270545f.png)

Herramienta para convertir los conjuntos de datos INSPIRE de los Servicios ATOM 
del Catastro Español (http://www.catastro.minhap.gob.es/webinspire/index.html) 
a archivos OSM. Esto es parte de una importación en curso:

https://openstreetmap.es/catastro

Requisitos
----------

Docker https://www.docker.com/get-started

Instalación
-----------

Ver INSTALL.es.md (https://OSM-es.github.io/CatAtom2Osm/es/install.html).

Uso
---

Para ejecutar la aplicación:

    catatom2osm [OPCIÓN]... [RUTAS]

El argumento RUTAS indica los directorios para procesar municipios.
El nombre del último directorio en cada ruta debe ser 5 dígitos (GGMMM)
correspondientes al código de Oficina Provincial (GG) y Municipio (MMM).
Si el programa no encuentra los archivos de entrada los descargará de los
Servicios INSPIRE del Catastro Español.


**Opciones**:

* \-h, --help                Muestra este mensaje de ayuda y sale
* \-v, --version             Muestra la versión del programa y sale
* \-l, --list                Lista códigos de provincia
* \-l [PROV], --list [PROV]  Lista códigos de municipios en PROV (2 dígitos)
* \-l [MUN], --list [MUN]    Lista límites administrativos para MUN (5 dígitos)
* \-b, --building            Procesa sólo el conjunto de datos de edificios
* \-d, --address             Procesa sólo el conjunto de datos de direcciones
* \-z, --zoning              Procesa sólo el conjunto de datos de tareas
* \-s SPLIT, --split SPLIT   Procesa los datos en las zonas delimitadas por SPLIT (archivo / id OSM o nombre del límite administrativo)
* \-m, --manual              Desactiva la combinación con datos OSM
* \-c, --comment             Recupera los metadatos de las tareas
* \-w, --download            Solo descargar
* \--log=log_level           Selecciona el nivel de registro entre DEBUG, INFO, WARNING, ERROR o CRITICAL.
* \-f CONFIG_FILE, --config-file CONFIG_FILE  Ruta al archivo de configuración. Por defecto es 'config.yaml'
* \-g, --generate-config     Genera un archivo de muestra con la configuración por defecto

Más información sobre la opción 'split' en la [wiki](https://wiki.openstreetmap.org/wiki/ES:Catastro_espa%C3%B1ol/Importaci%C3%B3n_de_edificios/Gesti%C3%B3n_de_proyectos#Anexo:_Modificar_proyectos)

Configuración
-------------

El programa usa la configuración de localización del sistema para seleccionar el idioma en la traducción de los tipos de nombres de viales. Si quieres usar otro, asigna la variable de entorno LANG. Por ejemplo, en Linux:

	LANG=es_ES.UTF-8; catatom2osm

Para forzar a usar Español.

	LANG=ca_ES.UTF-8; catatom2osm

Para forzar a usar Catalán.

	LANG=gl_ES.UTF-8; catatom2osm

Para forzar a usar Gallego.

En la ventana de comandos de Windows (CMD):

   set LANG=ca_ES.UTF-8 && catatom2osm

En PowerShell:

   ${LANG}="ca_ES.UTF-8"; catatom2osm

Para más opciones y cambios permantes, usa el archivo de configuración. 

Crea una plantilla del archivo con:

   catatom2osm -g

Estos son los parámetros a modificar:

* language: Idioma para traducir los nombres de viales: es_ES ca_ES gl_ES
* highway_types: Diccionario para traducir los tipos de vias.
* place_types: lista de tipos de vía que se traducen a direcciones de lugar (addr:place).
* remove_place_from_name: Lista de tipos de vía a eliminar del nombre.
* excluded_types: Lista de tipos de vía que no se analizarán.
* warning_min_area: Área en m² para el aviso de área pequeña.
* warning_max_area: Área en m² para el aviso de área grande.
* parcel_parts: Número de partes de edificio para agregar parcelas.
* parcel_dist: Distancia en metros para agregar parcelas.

Documentación
-------------

Consulta la documentación del programa.

https://OSM-es.github.io/CatAtom2Osm/es

