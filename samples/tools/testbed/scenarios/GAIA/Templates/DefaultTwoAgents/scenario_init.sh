# Scenario Init.
mkdir coding
if [ -f "gaia_files/__FILE_NAME__" ] ; then
    mv "gaia_files/__FILE_NAME__" coding/.
fi
rm -Rf gaia_files
