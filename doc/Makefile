# Makefile for lilypondToBandVideoConverter documentation

PREFIX = lilypondToBandVideoConverter
TARGETPDF = $(PREFIX).pdf
LATEXSOURCE = $(PREFIX).ltx
FIGURESOURCE = ltbvcFigure.mp
INTERMEDIATEFIGURELIST = ltbvcFigure-1.mps ltbvcFigure-2.mps \
                         ltbvcFigure-3.mps ltbvcFigure-4.mps \
                         ltbvcFigure-5.mps
TARGETFIGURELIST = figures/dependencyDiagram.mps \
                   figures/preprocessingPhaseDependencies.mps \
                   figures/postprocessingPhaseDependencies.mps \
                   figures/trackMixdown.mps \
                   figures/videoTargetDimensions.mps \

METAPOST = mpost -s prologues=3

#-------------------
#- general targets -
#-------------------

all: $(TARGETPDF)

#--

clean:
	$(RM) $(TARGETPDF)
	$(RM) *.mps *.mpx
	$(RM) $(PREFIX).aux $(PREFIX).lof *.log $(PREFIX).toc
	$(RM) figures/*.mps

#----------------
#- file targets -
#----------------

$(INTERMEDIATEFIGURELIST): $(FIGURESOURCE)
	$(METAPOST) $<

#--

figures/dependencyDiagram.mps: ltbvcFigure-1.mps
	cp $< $@

figures/preprocessingPhaseDependencies.mps: ltbvcFigure-2.mps
	cp $< $@

figures/postprocessingPhaseDependencies.mps: ltbvcFigure-3.mps
	cp $< $@

figures/videoTargetDimensions.mps: ltbvcFigure-4.mps
	cp $< $@

figures/trackMixdown.mps: ltbvcFigure-5.mps
	cp $< $@

#--

$(TARGETPDF): $(LATEXSOURCE) $(TARGETFIGURELIST)
	pdflatex $(LATEXSOURCE)
	pdflatex $(LATEXSOURCE)
