if ( $LANG -eq $null ) {
    Get-WinSystemLocale -OutVariable system_locale | Out-Null
    ${LANG}=$system_locale.name + ".UTF-8"
}
docker pull egofer/catatom2osm
docker run --rm -it -e LANG="$LANG" -v ${PWD}:/catastro egofer/catatom2osm catatom2osm $args
