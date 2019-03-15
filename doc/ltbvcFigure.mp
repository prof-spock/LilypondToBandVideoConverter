outputtemplate := "%j-%c.mps";
%prologues := 3;

input boxes

%========================================
% SUPPORT FUNCTIONS
%========================================

pair nullVector;
nullVector := (0mm, 0mm);

verbatimtex
  \def\stkB#1#2{$\displaystyle{\matrix{{\rm\hbox{#1}}\cr{\rm\hbox{#2}}\cr}}$}
  \def\stkC#1#2#3{$\displaystyle{\matrix{{\rm\hbox{#1}}\cr{\rm\hbox{#2}}\cr{\rm\hbox{#3}}\cr}}$}
etex

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

def addDirectFlow (suffix a, b) =
  % draw a single arrow path between box objects <a> and <b> at their
  % boundaries with the path leaving <a> on the right and entering <b>
  % from the left using a black dashed line
  
  path currentPath;

  currentPath := a.e .. 1/2[b.w,b.c];
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
% General Box
%========================================

def Box_make (suffix shape)(expr kind)(expr text) =
  % makes a box called <shape> with background filled with <text>

  if kind = "C":
    circleit.shape(text);
  elseif kind = "B":
    boxit.shape(text);
  else:
    boxit.shape(text);
  fi
enddef;

%========================================

def Box_setBoxPositions (text shapeList)(expr startPosition)(expr offset) =
  % sets center positions for shapes in <shapeList> starting at
  % <startPosition> with <offset>

  pair previousPosition;

  previousPosition := startPosition;

  forsuffixes shape = shapeList:
    shape.c = previousPosition;
    previousPosition := previousPosition + offset;
  endfor
enddef;

%========================================

def Box_setSizeAndColor (suffix shape)(expr size)(expr fillColor) =
  % defines size of <shape> to be <size> and fill color to be
  % <fillColor>

  shape.n - shape.w = 1/2 size;
  fill bpath.shape withcolor fillColor; 
enddef;

%========================================
% Phase Or File Boxes
%========================================

def PhaseOrFileBox_makeAll =
  % makes all processing box for phases and files

  Box_make(fileLilypond, "B", btex \stkB{lilypond}{file} etex);
  Box_make(fileConfig, "B", btex \stkB{configuration}{file} etex);

  % preprocessing phases
  Box_make(phaseExtract, "C", btex extract etex);
  Box_make(phaseScore, "C", btex score etex);
  Box_make(phaseMidi, "C", btex midi etex);
  Box_make(phaseSilentVideo, "C", btex silentvideo etex);

  Box_make(fileExtract, "FM", btex \stkC{voice}{extract}{files} etex);
  Box_make(fileScore, "B", btex \stkB{score}{file} etex);
  Box_make(fileMidi, "B", btex \stkB{midi}{file} etex);
  Box_make(fileSilentVideo, "FM", btex \stkC{silent}{video}{files} etex);
  Box_make(fileSubtitleText, "B", btex \stkC{subtitle}{text}{file} etex);

  % postprocessing phases
  Box_make(phaseRawAudio, "C", btex rawaudio etex);
  Box_make(phaseRefinedAudio, "C", btex refinedaudio etex);
  Box_make(phaseMixdown, "C", btex mixdown etex);
  Box_make(phaseFinalVideo, "C", btex finalvideo etex);

  Box_make(fileRawAudio, "FM", btex \stkC{raw}{audio}{files} etex);
  Box_make(fileRefinedAudio, "FM", btex \stkC{refined}{audio}{files} etex);
  Box_make(fileAudio, "FM", btex \stkC{mix}{audio}{files} etex);
  Box_make(fileVideo, "FM", btex \stkB{video}{files} etex);
enddef;

%========================================

def PhaseOrFileBox_setPostprocessingBoxes (expr startPosition) =
  % sets up the position and size of postprocessing phases and extracts

  Box_setBoxPositions(phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo)
                     (startPosition, PhaseOrFileBox_phaseOffsetVector);

  Box_setBoxPositions(fileRawAudio, fileRefinedAudio, fileAudio, fileVideo)
                     (phaseRawAudio.c + PhaseOrFileBox_resultOffsetVector,
                      PhaseOrFileBox_phaseOffsetVector)
enddef;

%========================================

def PhaseOrFileBox_setPostprocessingEdges =
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

def PhaseOrFileBox_setPreprocessingBoxes (expr startPosition) =
  % sets up the position and size of preprocessing phases and extracts

  Box_setBoxPositions(phaseExtract, phaseScore, phaseMidi, phaseSilentVideo)
                        (startPosition, PhaseOrFileBox_phaseOffsetVector);
  
  Box_setBoxPositions(fileExtract, fileScore, fileMidi, fileSilentVideo)
                        (phaseExtract.c + PhaseOrFileBox_resultOffsetVector,
                         PhaseOrFileBox_phaseOffsetVector);

  fileSubtitleText.c = fileSilentVideo.c
                       + (0, ypart PhaseOrFileBox_phaseOffsetVector);
enddef;

%========================================

def PhaseOrFileBox_setPreprocessingEdges =
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
% Phase and File Box Configuration
%========================================

pair PhaseOrFileBox_fileBoxSize;
pair PhaseOrFileBox_phaseBoxSize;
pair PhaseOrFileBox_phaseOffsetVector;
pair PhaseOrFileBox_resultOffsetVector;
color PhaseOrFileBox_fileFillColor;
color PhaseOrFileBox_configFileFillColor;
color PhaseOrFileBox_lilypondFileFillColor;
color PhaseOrFileBox_phaseFillColor;

PhaseOrFileBox_configFileFillColor   := (0.8,  0.85, 0.8 );
PhaseOrFileBox_lilypondFileFillColor := (0.8,  0.8,  0.85);
PhaseOrFileBox_fileFillColor         := (1.0, 1.0, 0.75);
PhaseOrFileBox_fileBoxSize           := (20mm, 15mm);
PhaseOrFileBox_phaseFillColor        := (0.9, 0.8, 0.9);
PhaseOrFileBox_phaseBoxSize          := (20mm, 15mm);
PhaseOrFileBox_phaseOffsetVector     := (12mm, -20mm);
PhaseOrFileBox_resultOffsetVector    := (30mm,   0mm);

%========================================
% Voice and Mastering Boxes
%========================================

def VoiceBox_makeAll =
  % position all boxes for voices in voice and mastering image

  Box_make(voiceA, "B", btex audio for voice${}_1$ etex);
  Box_make(voiceB, "B", btex audio for voice${}_2$ etex);
  Box_make(voiceDot, "B", btex ... etex);
  Box_make(voiceC, "B", btex audio for voice${}_n$ etex);

  Box_setBoxPositions(voiceA, voiceB, voiceDot, voiceC)
                     (VoiceBox_topCenterPosition, VoiceBox_offset);

  Box_setSizeAndColor(voiceDot, VoiceBox_size, white);

  forsuffixes shape = voiceA, voiceB, voiceC:
    Box_setSizeAndColor(shape, VoiceBox_size, VoiceBox_fillColor);
    drawboxed(shape);
  endfor

  drawunboxed(voiceDot);
enddef;

%========================================

def MasteringBox_layoutSingleTrack (text internalShapeList)
                                   (suffix groupShape)
                                   (expr groupCenterPosition)
                                   (expr groupShapeSize)
                                   (expr internalShapeSize) =
  % position all mastering boxes for a single track in voice and
  % mastering image; <internalShapeList> is the list of processing
  % stage shapes, <groupShape> the surrounding group,
  % <groupCenterPosition> the center position of the group shape and
  % <internalShapeSize> the size of the stage shapes

  numeric internalBoxXOffset;
  numeric internalBoxXSize;
  numeric internalBoxCount;
  pair firstBoxPosition;

  groupShape.c = groupCenterPosition;
  Box_setSizeAndColor(groupShape, groupShapeSize, MasteringGroup_fillColor);
  drawboxed(groupShape);
  
  internalShapeCount := 3;
  internalShapeXSize := xpart internalShapeSize;
  internalShapeXOffset := ((xpart groupShapeSize) / internalShapeCount
                          - internalShapeXSize);
  firstBoxPosition := groupShape.w
                      + (internalShapeXSize + internalShapeXOffset, 0mm)/2;
  Box_setBoxPositions(internalShapeList)
                      (firstBoxPosition,
                       (internalShapeXSize + internalShapeXOffset, 0mm));

  forsuffixes shape = internalShapeList:
    Box_setSizeAndColor(shape,internalShapeSize, MasteringBox_fillColor);
    drawboxed(shape);
  endfor
enddef;

%========================================

def MasteringBox_makeAll =
  % position all mastering boxes for voice and mastering image
  
  Box_make(masteringGroupA, "B", "");
  Box_make(mixerBoxA, "B",
           btex \stkB{mixdown${}_A$~by}{\tt voiceNameToAudioLevelMap} etex
           rotated 90);
  Box_make(masteringBoxA, "B",
           btex \stkB{mastering${}_A$~via}{\tt masteringCommandList} etex
           rotated 90);
  Box_make(attenuationBoxA, "B",
           btex \stkB{attenuation${}_A$~by}{\tt attenuationLevel} etex
           rotated 90);
  MasteringBox_layoutSingleTrack(mixerBoxA, masteringBoxA, attenuationBoxA)
                                (masteringGroupA,
                                 MasteringGroupA_centerPosition,
                                 MasteringGroupA_size,
                                 MasteringBoxA_size);

  Box_make(masteringGroupK, "B", "");
  Box_make(mixerBoxK, "B", btex mixdown${}_K$ etex rotated 90);
  Box_make(masteringBoxK, "B", btex mastering${}_K$ etex rotated 90);
  Box_make(attenuationBoxK, "B", btex attenuation${}_K$ etex rotated 90);
  MasteringBox_layoutSingleTrack(mixerBoxK, masteringBoxK, attenuationBoxK)
                                (masteringGroupK,
                                 MasteringGroupK_centerPosition,
                                 MasteringGroupK_size,
                                 MasteringBoxK_size);
  Box_make(masteringGroupDot, "B", "...");
  masteringGroupDot.c = 1/2[masteringGroupA.s, masteringGroupK.n];
  Box_setSizeAndColor(masteringGroupDot, MasteringGroupDot_size, white);
  drawunboxed(masteringGroupDot);  
enddef;

%========================================

def TrackBox_makeAll =
  % position all track boxes for voice and mastering image
  
  Box_make(trackBoxA, "B", btex audio for track${}_A$ etex);
  Box_make(trackBoxDot, "B", "...");
  Box_make(trackBoxK, "B", btex audio for track${}_K$ etex);
  trackBoxA.w = (TrackBox_xPosition, ypart masteringGroupA.e);
  trackBoxDot.w = (TrackBox_xPosition, ypart masteringGroupDot.e);
  trackBoxK.w = (TrackBox_xPosition, ypart masteringGroupK.e);

  forsuffixes shape = trackBoxA, trackBoxK:
    Box_setSizeAndColor(shape, TrackBox_size, VoiceBox_fillColor);
    drawboxed(shape);
  endfor

  Box_setSizeAndColor(trackBoxDot, TrackBox_size, white);
  drawunboxed(trackBoxDot);
enddef;

%========================================

def VoiceAndMasteringBox_setEdges =
  % sets up the edges of postprocessing phases and extracts

  forsuffixes shape = voiceA, voiceB, voiceC:  
    addDirectFlow(shape, mixerBoxA);
    addDirectFlow(shape, mixerBoxK);
  endfor

  addForwardFlow(mixerBoxA, masteringBoxA);
  addForwardFlow(masteringBoxA, attenuationBoxA);
  addForwardFlow(attenuationBoxA, trackBoxA);
  addForwardFlow(mixerBoxK, masteringBoxK);
  addForwardFlow(masteringBoxK, attenuationBoxK);
  addForwardFlow(attenuationBoxK, trackBoxK);
enddef;

%========================================

def VoiceAndMasteringBox_makeAll =
  % position all boxes for voice and mastering image

  VoiceBox_makeAll;
  MasteringBox_makeAll;
  TrackBox_makeAll;
  VoiceAndMasteringBox_setEdges;
enddef;

%========================================
% Voice and Mastering Box Configuration
%========================================

color MasteringBox_fillColor;
color MasteringGroup_fillColor;
pair MasteringBoxA_size;
pair MasteringGroupA_size;
pair MasteringGroupA_centerPosition;
pair MasteringBoxK_size;
pair MasteringGroupDot_size;
pair MasteringGroupK_size;
pair MasteringGroupK_centerPosition;
numeric MasteringGroup_xSize;
pair TrackBox_size;
numeric TrackBox_xPosition;
color VoiceBox_fillColor;
pair VoiceBox_offset;
pair VoiceBox_size;
pair VoiceBox_topCenterPosition;

MasteringBox_fillColor     := (0.0, 1.0, 1.0);
MasteringBoxA_size         := (15mm, 50mm);
MasteringBoxK_size         := (10mm, 25mm);
MasteringGroup_fillColor   := (0.0, 0.7, 0.7);
MasteringGroup_xSize       := 15mm + 3*xpart MasteringBoxA_size;
MasteringGroupA_size       := (MasteringGroup_xSize,
                               5mm + ypart MasteringBoxA_size);
MasteringGroupDot_size     := (MasteringGroup_xSize, 10mm);
MasteringGroupK_size       := (MasteringGroup_xSize,
                               5mm + ypart MasteringBoxK_size);

VoiceBox_fillColor         := (0.9, 0.9, 0.0);
VoiceBox_offset            := (0mm, -20mm);
VoiceBox_size              := (25mm, 10mm);
TrackBox_size              := (30mm, 10mm);
VoiceBox_topCenterPosition := (xpart VoiceBox_size/2, 85mm);

MasteringGroupA_centerPosition := VoiceBox_topCenterPosition
                                  + (40mm + MasteringGroup_xSize/2, 5mm);
MasteringGroupK_centerPosition := (xpart MasteringGroupA_centerPosition,
                                   20mm);
TrackBox_xPosition             := xpart MasteringGroupA_centerPosition
                                  + MasteringGroup_xSize/2 + 20mm;

%========================================
%========================================
beginfig(1);
  color fillColor;
  pair configBoxSize;

  PhaseOrFileBox_makeAll;

  fileLilypond.w = (0mm, 80mm);
  fileConfig.w   = (40mm,  15mm);
  configBoxSize := (135mm, 15mm);
  Box_setSizeAndColor(fileLilypond, PhaseOrFileBox_fileBoxSize,
                      PhaseOrFileBox_lilypondFileFillColor);
  Box_setSizeAndColor(fileConfig, configBoxSize,
                      PhaseOrFileBox_configFileFillColor);

  PhaseOrFileBox_setPreprocessingBoxes((45mm, 120mm));
  PhaseOrFileBox_setPostprocessingBoxes(phaseExtract.c + (90mm, 0mm));

  forsuffixes shape = fileExtract, fileScore, fileMidi, fileSilentVideo,
                      fileSubtitleText,
                      fileRawAudio, fileRefinedAudio, fileAudio, fileVideo:
      Box_setSizeAndColor(shape, PhaseOrFileBox_fileBoxSize,
	PhaseOrFileBox_fileFillColor);
  endfor

  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo,
                      phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
      Box_setSizeAndColor(shape, PhaseOrFileBox_phaseBoxSize,
	                  PhaseOrFileBox_phaseFillColor);
  endfor

  % --- add all edges ---
  PhaseOrFileBox_setPreprocessingEdges;
  PhaseOrFileBox_setPostprocessingEdges;
  
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

  PhaseOrFileBox_makeAll;

  fileLilypond.w = (0mm, 80mm);
  fileConfig.w   = (40mm,  15mm);
  configBoxSize := (50mm, 15mm);
  Box_setSizeAndColor(fileLilypond, PhaseOrFileBox_fileBoxSize,
                      PhaseOrFileBox_lilypondFileFillColor);
  Box_setSizeAndColor(fileConfig, configBoxSize,
                      PhaseOrFileBox_configFileFillColor);

  PhaseOrFileBox_setPreprocessingBoxes((45mm, 120mm));

  forsuffixes shape = fileExtract, fileScore, fileMidi, fileSilentVideo,
                      fileSubtitleText:
    Box_setSizeAndColor(shape, PhaseOrFileBox_fileBoxSize,
 	                PhaseOrFileBox_fileFillColor);
  endfor

  forsuffixes shape = phaseExtract, phaseScore, phaseMidi, phaseSilentVideo:
    Box_setSizeAndColor(shape, PhaseOrFileBox_phaseBoxSize,
                        PhaseOrFileBox_phaseFillColor);
  endfor

  % --- add all edges ---
  PhaseOrFileBox_setPreprocessingEdges;
  
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

  PhaseOrFileBox_makeAll;

  fileConfig.w  = (40mm,  15mm);
  configBoxSize := (60mm, 15mm);
  Box_setSizeAndColor(fileConfig, configBoxSize,
                      PhaseOrFileBox_configFileFillColor);

  Box_setBoxPositions(fileMidi, fileSilentVideo)
                     ((20mm, 90mm), PhaseOrFileBox_phaseOffsetVector);
  fileSubtitleText.c = fileSilentVideo.c
                       + (0, ypart PhaseOrFileBox_phaseOffsetVector);
  
  PhaseOrFileBox_setPostprocessingBoxes(fileMidi.c + (40mm, 20mm));

  forsuffixes shape = fileMidi, fileSilentVideo, fileSubtitleText,
                      fileRawAudio, fileRefinedAudio, fileAudio, fileVideo:
    Box_setSizeAndColor(shape, PhaseOrFileBox_fileBoxSize,
                        PhaseOrFileBox_fileFillColor);
  endfor

  forsuffixes shape = phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                      phaseFinalVideo:
    Box_setSizeAndColor(shape, PhaseOrFileBox_phaseBoxSize,
                        PhaseOrFileBox_phaseFillColor);
  endfor

  % --- add all edges ---
  PhaseOrFileBox_setPostprocessingEdges;
  
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

  Box_make(videoTarget, "B", "");
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

%========================================
beginfig(5);
  VoiceAndMasteringBox_makeAll;
endfig;

end
