CC=pdflatex
CFLAGS=-shell-escape
# Needed by minted to call pygments.
BIB=bibtex
SPELLCHECK=aspell

PAPER=beamer.tex

TEX=$(wildcard content/*.tex)
AUX=$(wildcard *.aux)
FIGS_SVG=$(wildcard ../figs/SVG/*.svg)
FIGS_PDF=$(subst SVG,PDF,$(FIGS_SVG:.svg=.pdf))

# Get first PDF figure of FIGS_PDF with firstword then get its dirname with dir.
FIGS_PDF_DIR=$(dir $(firstword $(FIGS_PDF)))

all: $(FIGS_PDF)
	$(CC) $(CFLAGS) $(PAPER)

# For each figure in SVG convert it to PDF.
# We need to not export only the drawing for multiple figures.
# So, we call bash for that.
../figs/PDF/%.pdf: ../figs/SVG/%.svg
	@if [ ! -d $(FIGS_PDF_DIR) ]; then mkdir $(FIGS_PDF_DIR); fi
	echo 'python3 ../svg_export_fig.py $< -d ../figs/PDF';\
	python3 ../svg_export_fig.py -n $< -d ../figs/PDF;\

bib: $(AUX)
	for i in $^; do $(BIB) $$i; done

check: $(PAPER)
	# '-d fr' tells to use english dictionnary, '-t' is to use LaTeX mode
	# and '-c' is to check.
	for i in $^; do $(SPELLCHECK) -d fr -t -c $$i; done

clean:
	rm *.pdf *.aux *.bbl *.blg *.log *.out *.bcf *.lof *.lol *.lot *.toc *.xml

mr_proper: clean
	rm -r $(FIGS_PDF_DIR)
