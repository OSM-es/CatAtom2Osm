Registro de cambios
===================

**14-07-2023 (2.15.2)**
* Fix 2.14.1 sin direcciones si show_refs es false

**13-07-2023 (2.15.1)**
* Integra la generación de límites del municipio con el proceso normal.

**11-07-2023 (2.15.0)**
* Añade opción para generar límites del municipio.
* Mejora la localización del municipio si existe el archivo anterior.

**29-06-2023 (2.14.2)**
* Actualiza certifi para corregir catastro SSLCertVerificationError.
* Actualiza a urls https (actualmente redirige).

**16-06-2023 (2.14.1)**
* Correción para que nombre de la calle en Catastro salga en address.osm.

**14-06-2023 (2.14.0)**
* Incluye el nombre de la calle en Catastro junto con la referencia.
* Salida OSM XML en utf-8.

**13-06-2023 (2.13.1)**
* Opción para excluir direcciones por nombre de calle (DISEMINADOS)

**12-06-2023 (2.13.0)**
* Opción para incluir las referencias catastrales en los archivos de tareas.

**10-05-2023 (2.12.1)**
* Corrige error por el que no se independizaban los archivos de registro.

**25-04-2023 (2.12.0)**
* Elimina fixme 'Las partes de edificio no cubren todo el contorno'.

**22-04-2023 (2.11.2)**
* Capacidad para configurar formato de logs externamente.

**20-04.2023 (2.11.1)**
* Añade instancia cartobase de overpass.

**19-04-2023 (2.11.0)**
* Busca en línea municipios que no estén registrados préviamente (#114)
* Actualiza listado de municipios.

**03-12-2022 (2.10.4)**
* Resuelve error no copiaba zoning.zip a tasks

**08-11-2022 (2.10.3)**
* Resuelve error calculando posición media de relación al leer lugares de OSM #112
* Resuelve error no carga configuración definida por el usuario #113

**07-11-2022 (2.10.2)**
* Corrige error cuando falta el nombre a lugar

**13-10-2022 (2.10.1)**
* Pone nombres de place=square en addr:place

**02-09-2022 (2.10.0)**
* Combinación de nombres de lugares osm con direcciones

**29-08-2022 (2.9.20)**
* Incluye origen de conversión en highway_names.csv
* Corrige traducción del término feature

**23-08-2022 (2.9.19)**
* Muestra división al ejecutar
* Reorganiza carpetas de tareas

**18-08-2022 (2.9.18)**
* Comprime archivo de zonificación de tareas

**17-08-2022 (2.9.17)**
* Endurece la simplificación de nodos de la zonificación de tareas para evitar problemas al importar en Gestor de Tareas

**14-08-2022 (2.9.16)**
* Corrige salida de idioma en el informe
* Añade configuración de tareas en el informe

**12-08-2022 (2.9.15)**
* Corrige error mostrando divisiones de municipio cuando alguna está definida con una vía cerrada.

**09-08-2022 (2.9.14)**
* Opción para obtener información del conjunto de datos.

**01-07-2022 (2.9.13)**
* Incluye número de fixmes en archivo review.

**29-06-2022 (2.9.12)**
* Corrige recuento de direcciones cdau.
* Mejora mensaje de revisión final.
* Corrige error 'module' object is not callable.

**16-05-2022 (2.9.11)**
* Configuración dinámica de servidores overpass api.

**12-05-2022 (2.9.10)**
* Permite usuarios existentes en el archivo docker.

**11-05-2022 (2.9.9)**
* Corrige prints de depuración olvidados.

**23-04-2022 (2.9.8)**
* Restringe las direcciones CDAU a los límites de división.

**22-04-2022 (2.9.7)**
* Configuración dinámica de barras de progreso.

**20-04-2022 (2.9.6)**
* Configuración dinámica de idioma.

**19-04-2022 (2.9.5)**
* Opcionalmente oculta las barras de progreso.
* Pone los datos de división administrativa en el informe.

**13-04-2022 (2.9.4)**
* Actualiza ficheros de traducción y añade instrucciones para nuevos colaboradores (#109)
* Actualiza documentación LEEME
* Anota en el log valores de configuración inválidos (#108)

**09-04-2022 (2.9.3)**
* Registros separados por proceso.

**07-04-2022 (2.9.2)**
* Coge locale del sistema en los scripts de Windows.

**28-03-2022 (2.9.1)**
* Renombra módulo geo.aux, no es válido en Windows.

**27-03-2022 (2.9.0)**
* Añade archivo de cofiguración de usuario.

**14-03-2022 (2.8.2)**
* Elimina etiqueta de depuración dejada por error.

**11-03-2022 (2.8.1)**
* Error cargando proyecto por acentos.

**07-03-2022 (2.8.0)**
* Descarga archivos de límites administrativos para división de municipios.

**24-02-2022 (2.7.0)**
* Incorpora direcciones Carto BCN #35.
* Preserva tareas existentes al procesar por zonas.

**22-02-2022 (2.6.8)**
* Corrige varios errores #99, #100, #101, #102.

**21-02-2022 (2.6.7)**
* Corrige error al aplicar topología a partes incorrectas.

**21-02-2022 (2.6.6)**
* Corrige error asignando etiqueta a edificios abandonados.

**20-02-2022 (2.6.5)**
* Detecta códigos de municipio incorrectos #98.

**19-02-2022 (2.6.4)**
* Integra comprobación de estilo de código en cada commit #77.

**19-02-2022 (2.6.3)**
* Integra comprobación de estilo de código en publicación #77.

**18-02-2022 (2.6.2)**
* Corrige errores #92, #93, #95, #96.

**17-02-2022 (2.6.1)**
* Añade código de municipio a archivo de  proyecto.

**16-02-2022 (2.6.0)**
* Repartir los archivos de tareas por parcelas en lugar de zonas.
* Generar proyectos conteniendo sólo direcciones.
* Añade al proyecto recuento de partes de edificio como indicativo de complejidad de la tarea.
* Se abandona opción -o dividir proyecto usando códigos de zonas.

**05-01-2022 (2.5.3)**
* Corrige coordenadas CDAU

**03-01-2022 (2.5.2)**
* Incluye Jerez de la Frontera en CDAU

**03-01-2022 (2.5.1)**
* Corrige referencia a layer

**30-01-2022 (2.5.0)**
* Procesa con capas en memoria mucho más rápido.
* Evita mover entradas a paredes compartidas con otro edificio.
* Deja de generar salida para visualizar combinación de edificios.

**23-01-2022 (2.4.0)**
* Elimina partes sin edificio asociado #86

**22-01-2022 (2.3.0)**
* Corrige error asignando entradas múltiples a edificio
* Crea subdirectorio de salvaguardia para municipios fraccionados
* Corrige estadísticas de direcciones para municipios fraccionados
* Corrige detección incorrecta de zonas vacías
* Fija nivel del archivo de log en DEBUG
* Evita mensaje incorrecto con -z
* Procesar edificios sin zona #88
* Recorta zonificación cuando se usa -o

**21-01-2022 (2.2.2)**
* Mejora la definición de la zona de búsqueda en Overpass

**20-01-2022 (2.2.1)**
* Lanza error si se pasa una zona -o que no existe
* Control de flujo cuando no hay datos a procesar
* Corrige nombre de carpeta para opción -o

**20-01-2022 (2.2.0)**
* Almacenar nombres de municipio y áreas de búsqueda #82 #87

**16-01-2022 (2.1.0)**
* Añade direcciones tipo entrada asociadas a varios edificios
* Corrige error moviendo proyecto
* Corrige error por mantener shapefiles en modo depuración

**14-01-2022 (2.0.0)**
* Actualiza a Ubuntu 20.04 / QGIS3 / python3 #67.
* Simplifica la interfaz de línea de comandos.
* Permite procesar sólo direcciones por tareas (-d).

**10-01-2022 (1.9.3)**
* Corrige error eliminando elementos OSM.

**10-01-2022 (1.9.2)**
* Corrige área de búsqueda de overpass para la opción -s.

**08-01-2022 (1.9.1)**
* El polígono de recorte incluye zonas si el área superpuesta es mayor que el 50%.
* Corrige error renombrando proyecto.

**08-01-2022 (1.9.0)**
* Opción para dividir un municipio grande usando un archivo (#78)
* Corrección y mejora de rendimiento de opción -o (#73)

**21-12-2021 (1.8.7)**
* Resuelve aviso de ficheros sin cerrar en python3 (#67).
* Resuelve fallo uniendo entradas a vías building:part with QGIS3 (#67).
* Cambia método de instalación (en docker) por error en QGIS3 (#67)
* Corrige error de acceso a __main__.py
* Iguala resultados simplificación en python2/3 (#67).
* Nuevos scripts de utilidad (para desarrollo).

**20-12-2021 (1.8.6)**
*  Considerar bilinguismo y capitalización para asignar lugares #71.

**19-12-2021 (1.8.5)**
* Integra tests en publicación.

**19-12-2021 (1.8.4)**
* Corrige tarea para edificios sin zonificación (#70).

**19-12-2021 (1.8.3)**
* Actualiza cambios para poder descargar datos de CDAU.

**17-12-2021 (1.8.2)**
* Actualiza documentación de instalación.

**16-12-2021 (1.8.1)**
* Añade aviso para posibles zonas con geometría incorrecta.

**16-12-2021 (1.8.0)**
* Admite varios municipios o zonas.

**15-12-2021 (1.7.2)**
* Corrige error con zonificación de Madrid (#69).

**12-12-2021 (1.7.1)**
* Instalador para Windows (#59).

**11-12-2021 (1.7.0)**
* Simplifica instalación y uso de la imagen Docker  (#59, #66)

**10-12-2021 (1.6.1)**
* Deja de crear contorno para partes sin edificio

**10-12-2021 (1.6.0)**
* Opción para revisar las etiquetas de los changesets (#64)

**09-12-2021 (1.5.1)**
* Corrige etiqueta de zona en archivos de definición de tareas (#65)

**08-12-2021 (1.5.0)**
* Reorganización de ficheros de tareas (#65)

**03-12-2021 (1.4.0dev)**
* Opción para dividir municipios grandes por zonas (#58).
* Opción para listar zonas de un municipio (#58).

**15-11-2021 (1.3.10)**
* Simplificar configuración de idioma (#60).
* Añade la configuración del idioma al informe (#60).

**12-06-2021 (1.3.9)**
* Recomiendación para usar Docker.

**07-06-2021 (1.3.8)**
* Corrige error de versionado de Docker.

**07-06-2021 (1.3.7)**
* Añade autenticación de Docker en Travis.

**07-06-2021 (1.3.6)**
* Corrige error de sintaxis en Python3.

**14-04-2021 (1.3.5)**
* Añade la etiqueta 'generator' para identificar la versión en los conjuntos de cambios.

**07-04-2021 (1.3.4)**
* Evita fallar por archivos de zonificación rotos con zonas faltantes en Catastro.
* La opcion '-l' muestra las oficionas territoriales si no se pasa parámetro.

**09-03-2021 (1.3.3)**
* Corrige pruebas rotas en d851c4b (#56)

**09-03-2021 (1.3.2)**
* Actualiza los paquetes recomendados para python3 (#52)
* Actualiza URL en cdau.py (#54)

**09-03-2021 (1.3.1)**
* Añade 'fixme' cuando el área de las partes no coincida con la del edificio (#56).

**08-03-2021 (1.3)**
* Conserva todas las partes de los edificios para ajustarse mejor al estandar de Edificios 3D Sencillos (#56).

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
