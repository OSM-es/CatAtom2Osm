from setuptools import setup

from catatom2osm import __version__

setup(
    name='catatom2osm',
    version=__version__,
    description="Tool to convert INSPIRE data sets from the Spanish Cadastre ATOM Services to OSM files",
    author='Javier Sanchez Portero',
    author_email='javiersanp@gmail.com',
    url='https://github.com/OSM-es/CatAtom2Osm/',
    entry_points={
        'console_scripts': [
            'catatom2osm = catatom2osm:run',
        ],
    }
)