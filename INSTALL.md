=======
Install
=======

Docker
------

To ensure consistent results across all importers, the recommended procedure is to use the Docker image:
https://hub.docker.com/r/egofer/catatom2osm

1. Install docker:

* Windows: https://docs.docker.com/desktop/windows/install/
* Mac OS:  https://docs.docker.com/desktop/mac/install/
* Linux:   https://snapcraft.io/install/docker/ubuntu

2. Install the program launch scripts:

* Windows: https://github.com/OSM-es/CatAtom2Osm/raw/master/bin/catatom2osm.exe
* Linux/Mac OS:


    sudo curl https://github.com/OSM-es/CatAtom2Osm/raw/master/bin/catatom2osm.sh -o /usr/local/bin/catatom2osm && sudo chmod +x /usr/local/bin/catatom2osm

After this, the program will be available in the terminal shell:

    catatom2osm

To uninstall just remove the script:

    sudo rm /usr/local/bin/catatom2osm 

Development
-----------

If you want to contribute to the program, check CONTRIBUTING.md
