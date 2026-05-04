IMAGE="clitooltester/fedora43-sleuthkit-4.15.0"

INPUT=${HOME}/Projects/tests/test_data/ext/dftt-4
OUTPUT=/tmp/output

docker run \
	-u ${UID}:${GID} \
	-v "${INPUT}:/input:z" \
	-v "${OUTPUT}:/output:z" \
	${IMAGE} \
	/bin/bash -c "cd sleuthkit && TZ=UTC ./tools/fstools/istat /input/ext3-img-kw-1.dd 12 > /output/istat.12"

cat ${OUTPUT}/istat.12 | python3 istat2json.py | jq --sort-keys "."
