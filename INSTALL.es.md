===========
Instalación
===========

Docker
------

Para garantizar resultados homogeneos por todos los importadores, el procedimiento recomendado es usar la imagen Docker:
https://hub.docker.com/r/egofer/catatom2osm

1. Instalar docker:

* Windows: https://docs.docker.com/desktop/windows/install/
* Mac OS:  https://docs.docker.com/desktop/mac/install/
* Linux:   https://snapcraft.io/install/docker/ubuntu

2. Instala los scripts para lanzar el programa:

* Windows: https://github.com/OSM-es/CatAtom2Osm/raw/master/bin/catatom2osm.exe
* Linux/Mac OS:


    sudo curl https://raw.githubusercontent.com/OSM-es/CatAtom2Osm/master/bin/catatom2osm.sh -o /usr/local/bin/catatom2osm && sudo chmod +x /usr/local/bin/catatom2osm

Después de este paso, en la terminal de comandos estará disponible el programa:

    catatom2osm

Para desinstalar en Linux simplemente elimina el script:

    sudo rm /usr/local/bin/catatom2osm 

En Windows existe un deinstalador en la carpeta de instalación.

Desarrollo
----------

Si deseas contribuir al programa revisa CONTRIBUTING.md
