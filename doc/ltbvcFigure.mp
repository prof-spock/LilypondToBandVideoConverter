outputtemplate := "%j-%c.mps";
%prologues := 3;

input boxes

%========================================
% SUPPORT FUNCTIONS
%========================================

verbatimtex \def\stkB#1#2{$\displaystyle{\matrix{#1\cr#2\cr}}$} etex
verbatimtex \def\stkC#1#2#3{$\displaystyle{\matrix{#1\cr#2\cr#3\cr}}$} etex

%========================================

def arrowPath (suffix a, b)(expr linePath)(expr lineColor)(expr isDotted) =
  % draw a single arrow path given by <linePath> between box objects
  % <a> and <b> at their boundaries in color <lineColor> where
  % <isDotted> tells whether the line is dotted or dashed

  path currentPath;
  currentPath := linePath cutbefore bpath.a cutafter bpath.b;

  if isDotted:
    drawarrow currentPath dashed withdots withcolor lineColor
        withpen pencircle scaled 1pt;
  else:
    drawarrow currentPath dashed evenly withcolor lineColor
        withpen pencircle scaled 1pt;
  fi
enddef;

%========================================

def addBackwardFlow (suffix a, b) =
  % draw a single arrow path between box objects <a> and <b> at their
  % boundaries with the path leaving <a> on the right and entering <b>
  % from the left using a black dashed line
  
  path currentPath;
  currentPath := a.c .. b.c;
  arrowPath(a, b, currentPath, black, false);
enddef;

%========================================

def addForwardFlow (suffix a, b) =
  % draw a single arrow path between box objects <a> and <b> at their
  % boundaries with the path leaving <a> on the right and entering <b>
  % from the left using a black dashed line
  
  path currentPath;
  currentPath := a.e{right} .. {right}b.w;
  arrowPath(a, b, currentPath, black, false);
enddef;

%========================================

def addSupport (suffix a, b) =
  % draw a single arrow path between box objects <a> and <b> at their
  % boundaries with the path leaving <a> on the top and entering <b>
  % from the bottom using a black dotted line
  
  path currentPath;
  pair intermediatePointA, intermediatePointB;

  intermediatePointA = (xpart 1/2[a.c, b.c], ypart a.c);
  intermediatePointB = (xpart b.c, ypart a.n);
  currentPath := a.c .. intermediatePointA .. intermediatePointB
                 .. tension 4 .. {up}b.c;
  arrowPath(a, b, currentPath, 0.7white, true);
enddef;

%========================================
% Phase Or File Boxes
%========================================

def POFBox_make (suffix shape)(expr kind)(expr text) =
  % makes a box for phases or files called <shape> with background
  % filled with <text>

  if kind = "P":
    circleit.shape(text);
  elseif kind = "F":
    boxit.shape(text);
  else:
    boxit.shape(text);
  fi
enddef;

%========================================

def POFBox_setSizeAndColor (suffix shape)(expr size)(expr fillColor) =
  % defines size of <shape> to be <size> and fill color to be
  % <fillColor>

  shape.n - shape.w = 1/2 size;
  fill bpath.shape withcolor fillColor; 
enddef;

%========================================

def POFBox_makeAll =
  % makes all processing box for phases and files

  POFBox_make(fileLilypond, "F", btex \stkB{lilypond}{file} etex);
  POFBox_make(fileConfig, "F", btex \stkB{configuration}{file} etex);

  % preprocessing phases
  POFBox_make(phaseExtract, "P", btex extract etex);
  POFBox_make(phaseScore, "P", btex score etex);
  POFBox_make(phaseMidi, "P", btex midi etex);
  POFBox_make(phaseSilentVideo, "P", btex silentvideo etex);

  POFBox_make(fileExtract, "FM", btex \stkC{voice}{extract}{files} etex);
  POFBox_make(fileScore, "F", btex \stkB{score}{file} etex);
  POFBox_make(fileMidi, "F", btex \stkB{midi}{file} etex);
  POFBox_make(fileSilentVideo, "FM", btex \stkC{silent}{video}{files} etex);
  POFBox_make(fileSubtitleText, "F", btex \stkC{subtitle}{text}{file} etex);

  % postprocessing phases
  POFBox_make(phaseRawAudio, "P", btex rawaudio etex);
  POFBox_make(phaseRefinedAudio, "P", btex refinedaudio etex);
  POFBox_make(phaseMixdown, "P", btex mixdown etex);
  POFBox_make(phaseFinalVideo, "P", btex finalvideo etex);

  POFBox_make(fileRawAudio, "FM", btex \stkC{raw}{audio}{files} etex);
  POFBox_make(fileRefinedAudio, "FM", btex \stkC{refined}{audio}{files} etex);
  POFBox_make(fileAudio, "FM", btex \stkC{mix}{audio}{files} etex);
  POFBox_make(fileVideo, "FM", btex \stkB{video}{files} etex);
enddef;

%========================================

def POFBox_setBoxPositions (text shapeList)(expr startPosition)(expr offset) =
  % sets positions for shapes in <shapeList> starting at
  % <startPosition> with <offset>

  pair previousPosition;

  previousPosition := startPosition;

  forsuffixes shape = shapeList:
    shape.c = previousPosition;
    previousPosition := previousPosition + offset;
  endfor
enddef;

%========================================

def POFBox_setPostprocessingBoxes (expr startPosition) =
  % sets up the position and size of postprocessing phases and extracts

  POFBox_setBoxPositions(phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                         phaseFinalVideo)
                        (startPosition, POFBox_phaseOffsetVector);

  POFBox_setBoxPositions(fileRawAudio, fileRefinedAudio, fileAudio, fileVideo)
                        (phaseRawAudio.c + POFBox_resultOffsetVector,
                         POFBox_phaseOffsetVector)
enddef;

%========================================

def POFBox_setPostprocessingEdges =
  % sets up the edges of postprocessing phases and extracts

  addForwardFlow(fileMidi,          phaseRawAudio);
  addForwardFlow(phaseRawAudio,     fileRawAudio);
  addBackwardFlow(fileRawAudio,     phaseRefinedAudio);
  addForwardFlow(phaseRefinedAudio, fileRefinedAudio);
  addBackwardFlow(fileRefinedAudio, phaseMixdown);
  addForwardFlow(phaseMixdown,      fileAudio);
  addBackwardFlow(fileAudio,        phaseFinalVideo);
  addForwardFlow(fileSilentVideo,   phaseFinalVideo);
  addForwardFlow(fileSubtitleText,  phaseFinalVideo);
  addForwardFlow(phaseFinalVideo,   fileVideo);
enddef;

%========================================

def POFBox_setPreprocessingBoxes (expr startPosition) =
  % sets up the position and size of preprocessing phases and extracts

  POFBox_setBoxPositions(phaseExtract, phaseScore, phaseMidi, phaseSilentVideo)
                        (startPosition, POFBox_phaseOffsetVector);
  
  POFBox_setBoxPositions(fileExtract, fileScore, fileMidi, fileSilentVideo)
                        (phaseExtract.c + POFBox_resultOffsetVector,
                         POFBox_phaseOffsetVector);

  fileSubtitleText.c = fileSilentVideo.c + (0, ypart POFBox_phaseOffsetVector);
enddef;

%========================================

def POFBox_setPreprocessingEdges =
  % sets up the edges of preprocessing phases and extracts

  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo:
    addForwardFlow(fileLilypond, shape);
  endfor

  addForwardFlow(phaseExtract,     fileExtract);
  addForwardFlow(phaseScore,       fileScore);
  addForwardFlow(phaseMidi,        fileMidi);
  addForwardFlow(phaseSilentVideo, fileSilentVideo);
  addForwardFlow(phaseSilentVideo, fileSubtitleText);
enddef;

%========================================
% Configuration
%========================================

pair POFBox_fileBoxSize, POFBox_phaseBoxSize;
pair POFBox_phaseOffsetVector, POFBox_resultOffsetVector;
color POFBox_fileFillColor, POFBox_configFileFillColor;
color POFBox_lilypondFileFillColor;
color POFBox_phaseFillColor;

POFBox_configFileFillColor   := (0.8,  0.85, 0.8 );
POFBox_lilypondFileFillColor := (0.8,  0.8,  0.85);
POFBox_fileFillColor      := (1.0, 1.0, 0.75);
POFBox_fileBoxSize        := (20mm, 15mm);
POFBox_phaseFillColor     := (0.9, 0.8, 0.9);
POFBox_phaseBoxSize       := (20mm, 15mm);
POFBox_phaseOffsetVector  := (12mm, -20mm);
POFBox_resultOffsetVector := (30mm,   0mm);

%========================================
%========================================
beginfig(1);
  color fillColor;
  pair configBoxSize;

  POFBox_makeAll;

  fileLilypond.w = (0mm, 80mm);
  fileConfig.w   = (40mm,  15mm);
  configBoxSize := (135mm, 15mm);
  POFBox_setSizeAndColor(fileLilypond, POFBox_fileBoxSize,
                         POFBox_lilypondFileFillColor);
  POFBox_setSizeAndColor(fileConfig, configBoxSize,
                         POFBox_configFileFillColor);

  POFBox_setPreprocessingBoxes((45mm, 120mm));
  POFBox_setPostprocessingBoxes(phaseExtract.c + (90mm, 0mm));

  forsuffixes shape = fileExtract, fileScore, fileMidi, fileSilentVideo,
                      fileSubtitleText,
                      fileRawAudio, fileRefinedAudio, fileAudio, fileVideo:
    POFBox_setSizeAndColor(shape, POFBox_fileBoxSize, POFBox_fileFillColor);
  endfor

  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo,
                      phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
    POFBox_setSizeAndColor(shape, POFBox_phaseBoxSize, POFBox_phaseFillColor);
  endfor

  % --- add all edges ---
  POFBox_setPreprocessingEdges;
  POFBox_setPostprocessingEdges;
  
  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo,
                      phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
    addSupport(fileConfig, shape);
  endfor

  drawboxed(fileLilypond, fileConfig,
            phaseExtract, phaseScore, phaseMidi, phaseSilentVideo,
            fileExtract, fileScore, fileMidi, fileSilentVideo,
            fileSubtitleText,
            phaseRawAudio, phaseRefinedAudio, phaseMixdown,
            phaseFinalVideo, fileRawAudio, fileRefinedAudio,
            fileAudio, fileVideo);
endfig;

%========================================
beginfig(2);
  color fillColor;
  pair configBoxSize;

  POFBox_makeAll;

  fileLilypond.w = (0mm, 80mm);
  fileConfig.w   = (40mm,  15mm);
  configBoxSize := (50mm, 15mm);
  POFBox_setSizeAndColor(fileLilypond, POFBox_fileBoxSize,
                         POFBox_lilypondFileFillColor);
  POFBox_setSizeAndColor(fileConfig, configBoxSize, POFBox_configFileFillColor);

  POFBox_setPreprocessingBoxes((45mm, 120mm));

  forsuffixes shape = fileExtract, fileScore, fileMidi, fileSilentVideo,
                      fileSubtitleText:
    POFBox_setSizeAndColor(shape, POFBox_fileBoxSize, POFBox_fileFillColor);
  endfor

  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo:
    POFBox_setSizeAndColor(shape, POFBox_phaseBoxSize, POFBox_phaseFillColor);
  endfor

  % --- add all edges ---
  POFBox_setPreprocessingEdges;
  
  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo:
    addSupport(fileConfig, shape);
  endfor

  drawboxed(fileLilypond, fileConfig,
            phaseExtract, phaseScore, phaseMidi, phaseSilentVideo,
            fileExtract, fileScore, fileMidi, fileSilentVideo,
            fileSubtitleText);
endfig;

%========================================
beginfig(3);
  color fillColor;
  pair configBoxSize;

  POFBox_makeAll;

  fileConfig.w  = (40mm,  15mm);
  configBoxSize := (60mm, 15mm);
  POFBox_setSizeAndColor(fileConfig, configBoxSize,
                         POFBox_configFileFillColor);

  POFBox_setBoxPositions(fileMidi, fileSilentVideo)
                         ((20mm, 90mm), POFBox_phaseOffsetVector);
  fileSubtitleText.c = fileSilentVideo.c + (0, ypart POFBox_phaseOffsetVector);
  
  POFBox_setPostprocessingBoxes(fileMidi.c + (40mm, 20mm));

  forsuffixes shape = fileMidi, fileSilentVideo, fileSubtitleText,
                      fileRawAudio, fileRefinedAudio, fileAudio, fileVideo:
    POFBox_setSizeAndColor(shape, POFBox_fileBoxSize, POFBox_fileFillColor);
  endfor

  forsuffixes shape = phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
    POFBox_setSizeAndColor(shape, POFBox_phaseBoxSize, POFBox_phaseFillColor);
  endfor

  % --- add all edges ---
  POFBox_setPostprocessingEdges;
  
  forsuffixes shape = phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
    addSupport(fileConfig, shape);
  endfor

  drawboxed(fileConfig,
            fileMidi, fileSilentVideo, fileSubtitleText,
            phaseRawAudio, phaseRefinedAudio, phaseMixdown,
            phaseFinalVideo, fileRawAudio, fileRefinedAudio,
            fileAudio, fileVideo);
endfig;

end
