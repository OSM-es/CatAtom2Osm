# Install

## Linux

Install QGIS with the instructions in https://qgis.org

This is a summary of the commands to install QGIS 2.18.24 in Debian Jessie::

    su
    echo 'deb     https://qgis.org/debian-ltr jessie main' > /etc/apt/sources.list.d/qgis.list
    echo 'deb-src https://qgis.org/debian-ltr jessie main' >> /etc/apt/sources.list.d/qgis.list
    apt-key adv --keyserver keyserver.ubuntu.com --recv-key CAEB3DC3BDF7FB45
    apt update
    apt install qgis

This to install QGIS 3.2.3 in Ubuntu bionic::

    sudo echo 'deb     https://qgis.org/ubuntu bionic main' > /etc/apt/sources.list.d/qgis.list
    sudo echo 'deb-src https://qgis.org/ubuntu bionic main' >> /etc/apt/sources.list.d/qgis.list
    sudo apt-key adv --keyserver keyserver.ubuntu.com --recv-key CAEB3DC3BDF7FB45
    sudo apt update
    sudo apt install qgis

Clone the repository running::

    sudo apt install git python3-pip python3-dev python3-qgis #dependencies when using python3
    #sudo apt install git python-pip python-dev python-qgis #dependencies when using python2
    cd ~
    mkdir cadastre
    cd cadastre
    git clone https://github.com/OSM-es/CatAtom2Osm.git
    cd CatAtom2Osm
    sudo pip install -r requisites.txt
    sudo make install

After this, the program is available to run in the terminal.

    catatom2osm


## Mac OS X

Install QGIS3 from the QGIS download page
http://qgis.org

But before install the version of Python stated there:
http://python.org

Install GitHub desktop utility from
http://desktop.github.com

Run it and download this repository 
https://github.com/OSM-es/CatAtom2Osm.git

Open a command line shell and change the directory to the previously
downloaded CatAtom2Osm folder. Run this commands::

    cd Documents/GitHub/CatAtom2Osm
    sudo easy_install pip
    sudo pip3 install --update pip
    sudo pip3 install -r requisites.txt
    sudo make install

While you install the requisites you will be prompted to install the command
line developper tools, answer yes.

If necessary, edit the pyqgismac.sh file and change the locale value to the one aproppiate for your country.

After this, the program is available to run in the terminal.

    catatom2osm

It's suggested to run the code in a dedicate folder, for example.

    cd
    mkdir catastro
    cd catastro

Notes:

* Ignore the message "ERROR: Opening of authentication db FAILED"

### QGIS 2

If you want to install QGIS 2 instead of 3, these are the commands to run::

    cd Documents/GitHub/CatAtom2Osm
    sudo easy_install pip
    sudo pip install -r requisites.txt
    sudo make install


## Windows

Install QGIS using the OSGeo4W Network Installer (64 bits/ 32 bits) from
http://qgis.org download page.

* Run the installer and choose the Advanced Install option.
* Install from Internet
* Accept the default options
* From the Select packages screen select:

  * Desktop -> qgis: QGIS Desktop
  * Libs -> msvcrt 2008
  * Libs -> python3-devel
  * Libs -> python3-pip
  * Libs -> python3-setuptools

* Accept the list of unmet dependencies

Install Microsoft Visual C++ 14.0 Build Tools following the instructions in 
https://www.scivision.co/python-windows-visual-c++-14-required/

Install the GitHub desktop utility from desktop.github.com

Run it and download the repository https://github.com/OSM-es/CatAtom2Osm.git

In the previously downloaded CatAtom2Osm folder launch the file pyqgis3.bat. 
Write this in the resulting shell::

    python -m pip install -r requisites.txt

To use the program it will be necessary to run pyqgis3.bat to open a convenient 
Python QGIS shell. It's suggested to edit pyqgis3.bat, uncomment the penultimate
line with the CD command and enter the path of the folder where you want to 
download the Cadastre files. For example::

    cd c:\Users\YourName\Documents\cadastre

Notes:

* If the QGIS install aborts with this error "the code execution cannot proceed because zip.dll was not found", the only solution found is to use the 32 bits OSGeo4W installer instead of 64 bits.
* If during excecution you get error messages similar to "Failed to create file building_packed.shp: Permission denied", run from a simple folder (without special characters) hanging from the root, like: C:\Catastro


### QGIS 2

If you want to install QGIS 2 instead of 3, select these packages::

  * Desktop -> qgis-ltr: QGIS Desktop
  * Libs -> msvcrt 2008
  * Libs -> python-devel
  * Libs -> python-pip
  * Libs -> setuptools

Instead of Microsoft Visual C++ 14.0 Build Tools, install Microsoft Visual C++ Compiler for Python 2.7 from http://aka.ms/vcpython27

Open the the terminal with Python QGIS environment using the file pyqgis.bat.


## Development requeriments

Optionally, if you want to contribute to the program, install the development requeriments. In Linux and Macos:

    sudo pip install -r requisites-dev.txt
    
And to run the code tests:

    make test

In Windows::

    python -m pip install -r requisites-dev.txt
    
And to run the code tests::

    python -m unittest discover


Settings
========

The software by default use Spanish to transle the throughfare types. To use another language, edit the file 'setup.py'. Change 'es' to 'cat' for Catalan, or to 'gl' for Galician, in this lines:

   # Dictionary for default 'highway_types.csv'
   highway_types = highway_types_es

   # List of highway types to translate as place addresses
   place_types = place_types_es

   # List of place types to remove from the name
   remove_place_from_name = [place_types_es[26]]

