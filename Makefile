#
# This Makefile exists to make it easy to build this out of koji
#
_default:
	@echo "make"
sources:
	@echo "make sources"
	mkdir python-rpmpatch
	mv bin docs setup.py rpmpatch README.txt python-rpmpatch
	tar cf - python-rpmpatch | gzip --best > python-rpmpatch.tar.gz
