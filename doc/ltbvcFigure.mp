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
        withpen pencircle scaled 1.5pt;
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
  arrowPath(a, b, currentPath, 0.5red, true);
enddef;

%========================================

def drawDottedLine (expr startPosition)(expr lineVector) =
  % draws a dotted line from <startPosition> with direction <lineVector>

  pair endPosition;

  endPosition := startPosition + lineVector;
  draw startPosition -- endPosition dashed withdots
    withpen pencircle scaled 1.5pt;
enddef;

%========================================

def drawLabel (expr position)(expr alignment)(expr size)(text st) =
  % draws text <st> at <position> with <alignment>

  if alignment = "center":
    label(st infont defaultfont scaled size, position);
  elseif alignment = "left":
    label.lft(st infont defaultfont scaled size, position);
  elseif alignment = "right":
    label.rt(st infont defaultfont scaled size, position);
  fi
enddef;

%========================================

def drawMarker (expr startPosition)(expr markerLength)
               (expr arrowLength)(text direction) =
  % draws a marker line at <startPosition> with <markerLength> and an
  % arrow in <direction> with length <arrowLength>

  pair arrowStartPosition, arrowEndPosition;
  pair markerOffset, arrowOffset;
  pair markerEndPosition;
  
  if direction = "H":
    arrowOffset  := (arrowLength, 0);
    markerOffset := (0, markerLength);
  else:
    arrowOffset  := (0, arrowLength);
    markerOffset := (markerLength, 0);
  fi

  markerEndPosition := startPosition + markerOffset;
  draw startPosition -- markerEndPosition dashed evenly;

  arrowEndPosition   := 1/2[startPosition, markerEndPosition];
  arrowStartPosition := arrowEndPosition + arrowOffset;
  drawarrow arrowStartPosition -- arrowEndPosition;
enddef;

%========================================

def drawMarkerPair (expr startPosition)(expr vector)(expr markerLength)
                   (expr arrowLength)(text direction) =
  % draws two markers at <startPosition> and <endPosition> with
  % <markerLength> and an arrow in <direction> with length
  % <arrowLength>

  pair endPosition, positionOffset;

  if direction = "H":
    positionOffset := (xpart vector, 0);
  else:
    positionOffset := (0, ypart vector);
  fi

  endPosition := startPosition + positionOffset;
  drawMarker(startPosition, markerLength, arrowLength,  direction);
  drawMarker(endPosition,   markerLength, -arrowLength, direction);
enddef;

%========================================
% Phase Or File Boxes
%========================================

def Box_make (suffix shape)(expr kind)(expr text) =
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

def Box_setSizeAndColor (suffix shape)(expr size)(expr fillColor) =
  % defines size of <shape> to be <size> and fill color to be
  % <fillColor>

  shape.n - shape.w = 1/2 size;
  fill bpath.shape withcolor fillColor; 
enddef;

%========================================

def Box_makeAll =
  % makes all processing box for phases and files

  Box_make(fileLilypond, "F", btex \stkB{lilypond}{file} etex);
  Box_make(fileConfig, "F", btex \stkB{configuration}{file} etex);

  % preprocessing phases
  Box_make(phaseExtract, "P", btex extract etex);
  Box_make(phaseScore, "P", btex score etex);
  Box_make(phaseMidi, "P", btex midi etex);
  Box_make(phaseSilentVideo, "P", btex silentvideo etex);

  Box_make(fileExtract, "FM", btex \stkC{voice}{extract}{files} etex);
  Box_make(fileScore, "F", btex \stkB{score}{file} etex);
  Box_make(fileMidi, "F", btex \stkB{midi}{file} etex);
  Box_make(fileSilentVideo, "FM", btex \stkC{silent}{video}{files} etex);
  Box_make(fileSubtitleText, "F", btex \stkC{subtitle}{text}{file} etex);

  % postprocessing phases
  Box_make(phaseRawAudio, "P", btex rawaudio etex);
  Box_make(phaseRefinedAudio, "P", btex refinedaudio etex);
  Box_make(phaseMixdown, "P", btex mixdown etex);
  Box_make(phaseFinalVideo, "P", btex finalvideo etex);

  Box_make(fileRawAudio, "FM", btex \stkC{raw}{audio}{files} etex);
  Box_make(fileRefinedAudio, "FM", btex \stkC{refined}{audio}{files} etex);
  Box_make(fileAudio, "FM", btex \stkC{mix}{audio}{files} etex);
  Box_make(fileVideo, "FM", btex \stkB{video}{files} etex);
enddef;

%========================================

def Box_setBoxPositions (text shapeList)(expr startPosition)(expr offset) =
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

def Box_setPostprocessingBoxes (expr startPosition) =
  % sets up the position and size of postprocessing phases and extracts

  Box_setBoxPositions(phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                         phaseFinalVideo)
                        (startPosition, Box_phaseOffsetVector);

  Box_setBoxPositions(fileRawAudio, fileRefinedAudio, fileAudio, fileVideo)
                        (phaseRawAudio.c + Box_resultOffsetVector,
                         Box_phaseOffsetVector)
enddef;

%========================================

def Box_setPostprocessingEdges =
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

def Box_setPreprocessingBoxes (expr startPosition) =
  % sets up the position and size of preprocessing phases and extracts

  Box_setBoxPositions(phaseExtract, phaseScore, phaseMidi, phaseSilentVideo)
                        (startPosition, Box_phaseOffsetVector);
  
  Box_setBoxPositions(fileExtract, fileScore, fileMidi, fileSilentVideo)
                        (phaseExtract.c + Box_resultOffsetVector,
                         Box_phaseOffsetVector);

  fileSubtitleText.c = fileSilentVideo.c + (0, ypart Box_phaseOffsetVector);
enddef;

%========================================

def Box_setPreprocessingEdges =
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

pair Box_fileBoxSize, Box_phaseBoxSize;
pair Box_phaseOffsetVector, Box_resultOffsetVector;
color Box_fileFillColor, Box_configFileFillColor;
color Box_lilypondFileFillColor;
color Box_phaseFillColor;

Box_configFileFillColor   := (0.8,  0.85, 0.8 );
Box_lilypondFileFillColor := (0.8,  0.8,  0.85);
Box_fileFillColor      := (1.0, 1.0, 0.75);
Box_fileBoxSize        := (20mm, 15mm);
Box_phaseFillColor     := (0.9, 0.8, 0.9);
Box_phaseBoxSize       := (20mm, 15mm);
Box_phaseOffsetVector  := (12mm, -20mm);
Box_resultOffsetVector := (30mm,   0mm);

%========================================
%========================================
beginfig(1);
  color fillColor;
  pair configBoxSize;

  Box_makeAll;

  fileLilypond.w = (0mm, 80mm);
  fileConfig.w   = (40mm,  15mm);
  configBoxSize := (135mm, 15mm);
  Box_setSizeAndColor(fileLilypond, Box_fileBoxSize,
                         Box_lilypondFileFillColor);
  Box_setSizeAndColor(fileConfig, configBoxSize,
                         Box_configFileFillColor);

  Box_setPreprocessingBoxes((45mm, 120mm));
  Box_setPostprocessingBoxes(phaseExtract.c + (90mm, 0mm));

  forsuffixes shape = fileExtract, fileScore, fileMidi, fileSilentVideo,
                      fileSubtitleText,
                      fileRawAudio, fileRefinedAudio, fileAudio, fileVideo:
    Box_setSizeAndColor(shape, Box_fileBoxSize, Box_fileFillColor);
  endfor

  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo,
                      phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
    Box_setSizeAndColor(shape, Box_phaseBoxSize, Box_phaseFillColor);
  endfor

  % --- add all edges ---
  Box_setPreprocessingEdges;
  Box_setPostprocessingEdges;
  
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

  Box_makeAll;

  fileLilypond.w = (0mm, 80mm);
  fileConfig.w   = (40mm,  15mm);
  configBoxSize := (50mm, 15mm);
  Box_setSizeAndColor(fileLilypond, Box_fileBoxSize,
                         Box_lilypondFileFillColor);
  Box_setSizeAndColor(fileConfig, configBoxSize, Box_configFileFillColor);

  Box_setPreprocessingBoxes((45mm, 120mm));

  forsuffixes shape = fileExtract, fileScore, fileMidi, fileSilentVideo,
                      fileSubtitleText:
    Box_setSizeAndColor(shape, Box_fileBoxSize, Box_fileFillColor);
  endfor

  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo:
    Box_setSizeAndColor(shape, Box_phaseBoxSize, Box_phaseFillColor);
  endfor

  % --- add all edges ---
  Box_setPreprocessingEdges;
  
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

  Box_makeAll;

  fileConfig.w  = (40mm,  15mm);
  configBoxSize := (60mm, 15mm);
  Box_setSizeAndColor(fileConfig, configBoxSize,
                         Box_configFileFillColor);

  Box_setBoxPositions(fileMidi, fileSilentVideo)
                         ((20mm, 90mm), Box_phaseOffsetVector);
  fileSubtitleText.c = fileSilentVideo.c + (0, ypart Box_phaseOffsetVector);
  
  Box_setPostprocessingBoxes(fileMidi.c + (40mm, 20mm));

  forsuffixes shape = fileMidi, fileSilentVideo, fileSubtitleText,
                      fileRawAudio, fileRefinedAudio, fileAudio, fileVideo:
    Box_setSizeAndColor(shape, Box_fileBoxSize, Box_fileFillColor);
  endfor

  forsuffixes shape = phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
    Box_setSizeAndColor(shape, Box_phaseBoxSize, Box_phaseFillColor);
  endfor

  % --- add all edges ---
  Box_setPostprocessingEdges;
  
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

%========================================
beginfig(4);
  pair lineOffset, lineVector;
  pair marginOffset, markerLengthVector, markerPosition;
  pair videoTargetSize;
  numeric markerLength, arrowLength;
  numeric labelScaleFactor;

  videoTargetSize    := (50mm, 28mm);
  marginOffset       := (5mm, 4mm);
  markerLengthVector := (10mm, 5mm);
  labelScaleFactor   := 0.75;

  Box_make(videoTarget, "F", "");
  Box_setSizeAndColor(videoTarget, videoTargetSize, white);
  drawboxed(videoTarget);
  drawLabel(1/2[videoTarget.c, videoTarget.s], "center", 1.25,
            "VIDEO TARGET");

  lineOffset := (xpart marginOffset, 0);
  lineVector := (0, ypart videoTargetSize);
  drawDottedLine(videoTarget.sw + lineOffset, lineVector);
  drawDottedLine(videoTarget.se - lineOffset, lineVector);
  lineOffset := (0, ypart marginOffset);
  lineVector := (xpart videoTargetSize, 0);
  drawDottedLine(videoTarget.sw + lineOffset, lineVector);
  drawDottedLine(videoTarget.nw - lineOffset, lineVector);

  arrowLength := xpart videoTargetSize / 4;
  markerLength := -ypart markerLengthVector;
  drawMarkerPair(videoTarget.sw, videoTargetSize, markerLength,
                 arrowLength, "H");
  drawLabel(videoTarget.s + (0, markerLength)/2, "center", labelScaleFactor,
            "width");

  markerLength := ypart markerLengthVector;
  arrowLength  := xpart marginOffset / 2;
  markerPosition := videoTarget.nw + (xpart marginOffset, 0);
  drawMarkerPair(markerPosition, -marginOffset, markerLength, arrowLength, "H");
  drawMarkerPair(videoTarget.ne, -marginOffset, markerLength, arrowLength, "H");
  drawLabel(videoTarget.n + (0, markerLength)/2, "center", labelScaleFactor,
            "leftRightMargin");

  arrowLength := ypart videoTargetSize / 4;
  markerLength := xpart markerLengthVector;
  drawMarkerPair(videoTarget.se, videoTargetSize, markerLength,
                 arrowLength,  "V");
  drawLabel(videoTarget.e + (markerLength, 0)/2, "center", labelScaleFactor,
            "height");

  markerLength := -xpart markerLengthVector;
  arrowLength  := ypart marginOffset / 2;
  markerPosition := videoTarget.sw + (0, ypart marginOffset);
  drawMarkerPair(markerPosition, -marginOffset, markerLength, arrowLength, "V");
  drawMarkerPair(videoTarget.nw, -marginOffset, markerLength, arrowLength, "V");
  drawLabel(videoTarget.w, "left", labelScaleFactor, "topBottomMargin");

  markerLength := 1mm;
  arrowLength  := 2mm;
  markerPosition := 1/2[videoTarget.c, videoTarget.n];
  drawMarkerPair(markerPosition, -(1mm, 0), markerLength, arrowLength, "H");
  drawLabel(markerPosition - (0, 2markerLength), "center", labelScaleFactor,
            "resolution")
  
endfig;

end
