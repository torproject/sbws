# Minimal makefile for Sphinx documentation
#

# You can set these variables from the command line.
SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = simple-bw-scanner
SOURCEDIR     = source
BUILDDIR      = build
# generate SVG
IMAGEDIRS       = $(SOURCEDIR)/images
BUILDDIRIMAGES  = $(BUILDDIR)/html/_images
PYREVERSE     = pyreverse
PYREVERSE_FLAGS = -o svg -p sbws ../sbws
UMLSVG := $(PYREVERSE) $(PYREVERSE_FLAGS);mv *.svg $(IMAGEDIRS);mkdir -p $(BUILDDIRIMAGES);cp $(IMAGEDIRS)/*.svg $(BUILDDIRIMAGES)

# Put it first so that "make" without argument is like "make help".
help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: help Makefile

umlsvg:
	@echo "Generating UML SVG"
	$(UMLSVG)

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	# commented because if system packages invoke make html, it'll automatically
	# recreate the svg on every build, and it's not deterministic.
	#$(UMLSVG)
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
