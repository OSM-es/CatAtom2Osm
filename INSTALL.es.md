# Instalación

## Linux

Instalar QGIS siguiendo las instrucciones de https://qgis.org

Este es un resumen de la secuencia de comandos para instalar QGIS 2.18.24 en Debian Jessie::

    su
    echo 'deb     https://qgis.org/debian-ltr jessie main' > /etc/apt/sources.list.d/qgis.list
    echo 'deb-src https://qgis.org/debian-ltr jessie main' >> /etc/apt/sources.list.d/qgis.list
    apt-key adv --keyserver keyserver.ubuntu.com --recv-key CAEB3DC3BDF7FB45
    apt update
    apt install qgis

Este para QGIS 3.2.3 en Ubuntu bionic::

    sudo echo 'deb     https://qgis.org/ubuntu bionic main' > /etc/apt/sources.list.d/qgis.list
    sudo echo 'deb-src https://qgis.org/ubuntu bionic main' >> /etc/apt/sources.list.d/qgis.list
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key CAEB3DC3BDF7FB45
    sudo apt update
    sudo apt install qgis

Clonar el repositorio del programa ejecutando::

    sudo apt install git python-pip python-dev
    cd ~
    mkdir catastro
    cd catastro
    git clone https://github.com/OSM-es/CatAtom2Osm.git
    cd CatAtom2Osm
    sudo pip install -r requisites.txt
    sudo make install

Después de la instalación, el programa está disponible para ejecutar desde la terminal.

    catatom2osm


## Mac OS X

Instalar QGIS3 desde la página de descarga de QGIS
http://qgis.org 

Pero antes instalar la versión indicada allí de Python
http://python.org

Instalar el programa de escritorio de GitHub desde
http://desktop.github.com

Ejecutarlo y descargar el repositorio 
https://github.com/OSM-es/CatAtom2Osm.git

Abrir una consola de comandos (información adicional en este enlace)
https://www.soydemac.com/abrir-terminal-mac/

Ejecutar los comandos::

    cd Documents/GitHub/CatAtom2Osm
    sudo easy_install pip
    sudo pip3 install --update pip
    sudo pip3 install -r requisites.txt
    sudo make install

Durante la instalación de los requisitos pedirá la instalación de las 
herramientas para desarrolladores de la línea de comandos, responde que sí.

Si tu configuración regional es distinta de es_ES puedes editar el archivo pyqgismac.sh y cambiar las variables LANG, LC_CTYPE y LC_ALL

Después de la instalación, el programa está disponible para ejecutar desde la terminal.

    catatom2osm

Se sugiere ejecutar el programa en una carpeta dedicada, por ejemplo

    cd
    mkdir catastro
    cd catastro

Notas:

* Ignorar el mensaje "ERROR: Opening of authentication db FAILED"
* Si al instalar pip con easy_install sale un error relacionado con la versión del protocolo SSL, usar este comando

    curl https://bootstrap.pypa.io/get-pip.py | python

### QGIS 2

Si se desea instalar QGIS 2 en lugar de 3, los comandos a ejecutar son estos::

    cd Documents/GitHub/CatAtom2Osm
    sudo easy_install pip
    sudo pip install -r requisites.txt
    sudo make install


## Windows

Instalar QGIS usando el instalador OSGeo4W en red (64 bits/ 32 bits) desde la
página de descarga de http://qgis.org

* Ejecutar el instalador y seleccionar la opción Instalación Avanzada
* Instalar desde Internet
* Seleccionar las opciones por defecto
* En la pantalla de selección de paquetes seleccionar:

  * Desktop -> qgis: QGIS Desktop
  * Libs -> msvcrt 2008
  * Libs -> python3-devel
  * Libs -> python3-pip
  * Libs -> python3-setuptools

* Aceptar la lista de dependencias sugerida

Instalar Microsoft Visual C++ 14.0 Build Tools siguiendo las instrucciones de 
https://www.scivision.co/python-windows-visual-c++-14-required/

Instalar el programa de escritorio de GitHub desde desktop.github.com

Ejecutarlo y descargar el repositorio https://github.com/OSM-es/CatAtom2Osm.git

En la carpeta CatAtom2Osm descargada lanzar el archivo pyqgis3.bat. 
En la consola resultante ejecutar::

    python -m pip install -r requisites.txt

Será necesario ejecutar pyqgis3.bat cuando queramos usar el programa para abrir una consola de comandos con el entorno de Python QGIS adecuado. Se sugiere editar el archivo pyqgis3.bat, descomentar la penúltima línea con la orden CD e introducir la ruta de la carpeta donde se van a descargar los archivos de Catastro. Por ejemplo::

    cd c:\Users\TuNombre\Documents\catastro

Notas:

* Si la instalación de QGIS se aborta con el error "La ejecución de código no puede continuar porque no se encontró zip.dll", la única solución encontrada es usar el instalador OSGeo4W de 32 bits en lugar del de 64 bits.
* Si durante la ejecución del programa aparecen mensajes de error similares a "Failed to create file building_packed.shp: Permission denied", ejecutar en un directorio con nombre sencillo (sin caracteres espaciales) colgando del directorio raíz, por ejemplo: C:\Catastro


### QGIS 2

Si se desea instalar QGIS 2 en lugar de 3, seleccionar estos paquetes::

  * Desktop -> qgis-ltr: QGIS Desktop
  * Libs -> msvcrt 2008
  * Libs -> python-devel
  * Libs -> python-pip
  * Libs -> setuptools

En lugar de Instalar Microsoft Visual C++ 14.0 Build Tools, instalar Microsoft Visual C++ Compiler for Python 2.7 desde http://aka.ms/vcpython27

Abrir la consola con el entorno de Python QGIS usando el archivo pyqgis.bat.


## Entorno de pruebas

Opcionalmente, se puede instalar el entorno de pruebas para contribuir en el desarrollo del programa.
En Linux y Macos::

    sudo pip install -r requisites-dev.txt
    
Y para ejecutar las pruebas del código::

    make test

En Windows::

    python -m pip install -r requisites-dev.txt
    
Y para ejecutar las pruebas del código::

    python -m unittest discover

