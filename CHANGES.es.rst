Registro de cambios
===================

**09-03-2021 (1.3.1)**
* Añade 'fixme' cuando el área de las partes no coincida con la del edificio (#56).

**08-03-2021 (1.3)**
* Conserva todas las partes de los edificios para ajustarse mejor al estandar 
  de Edificios 3D Sencillos (#56).

**08-01-2020 (1.2.2)**
* Corrige TypeError: expected string or bytes-like object #49
* Corrige Infinite loop deleting invalid geometries #50

**07-01-2020 (1.2.1)**
* Resuelve referencia circular traduciendo compat.py
* Añade requisitos de desarrollo que faltaban

**07-01-2020 (1.2)**
* Versión compatible con Qgis 3.x

**18-12-2019 (1.1.14)**
* Asigna el dueño de la carpeta de la aplicación en docker

**17-12-2019 (1.1.13)**
* Corrige el nombre del repositorio Docker

**17-12-2019 (1.1.12)**
* Corrige el nombre del script de depliegue en docker

**17-12-2019 (1.1.11)**
* Despliega sólo a versiones etiquetadas
* Corrige el nombre del repositorio Docker

**17-12-2019 (1.1.10)**
* Añade contenedor docker e integración contínua con travis

**09-12-2019 (1.1.9)**

* Resuelve error tras actualización de archivos GML de Catastro #47

**09-11-2018 (1.1.8)**

* Resuelve error abriendo los archivos de Catastro más actuales (cuestión #29)
* Disminuye el tiempo de proceso para generar el archivo zoning.geojson de determinadas provincias (cuestión #26)
* Corrige errores en la traducción inglesa y unidades de memoria en el informe (por @javirg)

**29-05-2018 (1.1.7)**

* Añade traducción de nombres de calles en Gallego y Catalán.

**20-03-2018 (1.1.6)**

* Corrige errores menores.

**19-03-2018 (1.1.5)**

* Corrige errores menores.

**14-03-2018 (1.1.4)**

* Combina direcciones de Catastro con las del Callejero Digital Unificado de Andalucía (cuestión #11).

**13-03-2018 (1.1.3)**

* Elimina algunos prefijos (Lugar) de los nombres en las direcciones (cuestión #13).
* Pone enlaces a imágenes de fachada en address.osm (cuestión #14).
* Opción para sólamente descargar los archivos de Catastro (cuestión #16).

**02-03-2018 (1.1.2)**

* Corrige problema al abrir archivos OSM con parámetro upload=yes (cuestión #12)

**18-02-2018 (1.1.1)**

* Cambia el separador CSV a tabulador (cuestión #10)

**23-01-2018 (1.1.0)**

* Translada el repositorio a la organización OSM-es.
* address.geojson recoge todas las direcciones. Mejora #71.
* Comprime los archivos de tareas. Mejora #69.
* Listado de archivos de tareas a revisar (fixmes). Mejora #66.
* Elimina las direcciones de los tipos de vial configurados. Mejora #65.
* Translada los tipos vial a Catalan. Mejora #64.
* Mejora el comentario de los conjuntos de cambios. Mejora #63.

**16-01-2018 (1.0.5)**

* Comprime los archivos de tareas (cuestión #69).
* Corrige error (cuestión #62).

**01-01-2018 (1.0.2)**

* Mejoras en el fichero para definir proyectos en el gestor de tareas (cuestiones #58, #59 y #60).
* Corrige errores (cuestiones #57 y #61).

**30-12-2017 (1.0.1)**

* Corrige error menor en script de Macos.

**11-12-2017 (1.0.0)**

* Pasados tests en macOS Sierra 10.2, Debian 8.1.0 y Debian 9.3.0.
* Corregidos errores (cuestiones #53, #56).

**25-11-2017**

* Detecta piscinas encima de edificios (cuestión #51).

**22-11-2017**

* Ejecutadas las pruebas de código en Windows.
* Exporta los enlaces a imágenes en address.geojson.

**13-11-2017**

* Método alternativo para descargar los ficheros OSM para combinación de datos en municipios grandes.
* La opción -m deshabilita también la combinación de nombres de viales.

**09-11-2017**

* Elimina vértices en zig-zag y en punta.
* Detecta partes más grandes que el edificio al que pertenecen.

**06-11-2017**

* Genera informe de estadísticas (cuestión #50).

**31-10-2017**

* Reconstruye el código para mejorar la eficiencia (cuestiones #46, #48).
* Combinación de edificios/piscinas y direcciones existentes en OSM (cuestiones #43, #44, #49).

**11-07-2017**

* Corrige varios errores.
* Comprobación de alturas y área de edificios (cuestión #40).
* Añade etiquetas del conjunto de cambios a los ficheros OSM XML (cuestión #38).

**05-07-2017**

* Reduce los errores de validación de JOSM (cuestión #29)
* Mejora el código para hacerlo más rápido (cuestión #31)
* Mejora el método de simplificar nodos (cuestión #35)
* Mueve las entradas al contorno y fusiona las direcciones con los edificios (cuestiones #34, #33)
* Algunos fallos (cuestiones #25, #30, #32, #36, #37)
* Algunas mejoras (cuestiones #2, #7, #22, #23, #24, #26, #28)

**15-06-2017**

* Versión menor (cuestión #21)

**14-06-2017**

* Algunas mejoras y repara un fallo (cuestiones #16, #17, #18, #19, #20)

**13-06-2017**

* Repara algunos fallos (cuestiones #9, #10, #11, #12, #13, #14, #15).

**07-06-2017**

* Añade creación de ficheros de tareas (cuestión #5).

**05-06-2017**

* Añade creación de límites de tareas (cuestión #4).

**28-05-2017**

* Añade soporte para traducciones y traducción a español (cuestión #3).

**28-03-2017**

* Añade sporte para descargar los archivos fuente ATOM del Catastro (cuestión #1).

**22-03-2017**

* Reescribe simplificación y topología en ConsLayer.

**18-03-2017**

* Desarrollo inicial.
