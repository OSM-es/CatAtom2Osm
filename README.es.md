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

    catatom2osm <rutas>

El argumento ruta indica el directorio para los ficheros de entrada y salida.
El nombre del directorio debe comenzar con 5 dígitos (GGMMM) correspondientes 
al Código de Oficina Provincial del Catastro y Código de Municipio. Si el 
programa no encuentra los archivos de entrada los descargará de los Servicios 
INSPIRE del Catastro Español.

**Opciones**:

* \-h, --help                Muestra este mensaje de ayuda y termina
* \-v, --version             Imprime la versión de CatAtom2Osm y termina
* \-l [prov], --list [prov]  Lista los municipios disponibles para el código provincial de dos dígitos
* \--list-zones              Lista las etiquetas de las zonas del municipio
* \-t, --tasks               Reparte las construcciones en archivos de tareas (predeterminada, implica -z)
* \-c, --comment             Recupera los metadatos de las tareas
* \-b, --building            Procesa los edificios a un archivo individual en lugar de tareas
* \-d, --address             Procesa el conjunto de datos de direcciones
* \-z, --zoning              Procesa el conjunto de datos de zonificación catastral
* \-p, --parcel              Procesa el conjunto de datos de parcelas catastrales
* \-a, --all                 Procesa todos los conjuntos de datos (equivalente a -bdptz)
* \-o labels, --zone labels  Procesa zonas dadas sus etiquetas
* \-m, --manual              Desactiva la combinación con datos OSM
* \-w, --download            Solo descargar
* \--log=log_level           Selecciona el nivel de registro entre DEBUG, INFO, WARNING, ERROR o CRITICAL.

Configuración
-------------

El programa usa la configuración de localización del sistema para seleccionar el idioma en la traducción de los tipos de nombres de viales. Si quieres usar otro, asigna la variable de entorno LANG.

	LANG=es_ES.UTF-8; catatom2osm

Para forzar a usar Español.

	LANG=ca_ES.UTF-8; catatom2osm

Para forzar a usar Catalán.

	LANG=gl_ES.UTF-8; catatom2osm

Para forzar a usar Gallego.

Documentación
-------------

Consulta la documentación del programa.

https://OSM-es.github.io/CatAtom2Osm/es

