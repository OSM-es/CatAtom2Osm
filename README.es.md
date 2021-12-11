Léeme
=====

![](https://user-images.githubusercontent.com/1605829/141660065-1ad64b8f-dde9-4946-a4af-b556c270545f.png)

Herramienta para convertir los conjuntos de datos INSPIRE de los Servicios ATOM 
del Catastro Español (http://www.catastro.minhap.gob.es/webinspire/index.html) 
a archivos OSM. Esto es parte de una importación en curso:

https://wiki.openstreetmap.org/wiki/ES:Catastro_espa%C3%B1ol/Importaci%C3%B3n_de_edificios

Requisitos
----------

Docker https://www.docker.com/get-started

Instalación
-----------

Se recomienda usar la herramienta mediante esta imagen de Docker 
(https://hub.docker.com/r/egofer/catatom2osm).

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
* \--list-zones              Lista las etiquetas de las zonas del municipio
* \-t, --tasks               Reparte las construcciones en archivos de tareas (predeterminada, implica -z)
* \-b, --building            Procesa los edificios a un archivo individual en lugar de tareas
* \-d, --address             Procesa el conjunto de datos de direcciones
* \-z, --zoning              Procesa el conjunto de datos de zonificación catastral
* \-p, --parcel              Procesa el conjunto de datos de parcelas catastrales
* \-a, --all                 Procesa todos los conjuntos de datos (equivalente a -bdptz)
* \-o label, --zone label    Procesa una zona dada su etiqueta
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

