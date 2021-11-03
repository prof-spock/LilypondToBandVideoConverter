outputtemplate := "%j-%c.mps";
%prologues := 3;

input boxes;
input hatching;
input TEX;

%====================
% SUPPORT FUNCTIONS
%====================

pair nullVector;
nullVector := (0, 0);

verbatimtex
    \def\stkB#1#2{$\displaystyle{\matrix{{\rm\hbox{#1}}\cr{\rm\hbox{#2}}\cr}}$}
    \def\stkC#1#2#3{$\displaystyle{\matrix{{\rm\hbox{#1}}\cr{\rm\hbox{#2}}\cr{\rm\hbox{#3}}\cr}}$}
etex

%--------------------

def arrowPath (suffix a, b)(expr linePath, lineColor, isDotted) =
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

%--------------------

def addBackwardFlow (suffix a, b) =
    % draw a single arrow path between box objects <a> and <b> at
    % their boundaries with the path leaving <a> on the right and
    % entering <b> from the left using a black dashed line
  
    path currentPath;
    currentPath := a.c .. b.c;
    arrowPath(a, b, currentPath, black, false);
enddef;

%--------------------

def addForwardFlow (suffix a, b) =
    % draw a single arrow path between box objects <a> and <b> at
    % their boundaries with the path leaving <a> on the right and
    % entering <b> from the left using a black dashed line
  
    path currentPath;

    currentPath := a.e{right} .. {right}b.w;
    arrowPath(a, b, currentPath, black, false);
enddef;

%--------------------

def addDirectFlow (suffix a, b) =
    % draw a single arrow path between box objects <a> and <b> at
    % their boundaries with the path leaving <a> on the right and
    % entering <b> from the left using a black dashed line
  
    path currentPath;

    currentPath := a.e .. 1/2[b.w,b.c];
    arrowPath(a, b, currentPath, black, false);
enddef;

%--------------------

def addSupport (suffix a, b) =
    % draw a single arrow path between box objects <a> and <b> at
    % their boundaries with the path leaving <a> on the top and
    % entering <b> from the bottom using a black dotted line
  
    path currentPath;
    pair intermediatePointA, intermediatePointB;

    intermediatePointA = (xpart 1/2[a.c, b.c], ypart a.c);
    intermediatePointB = (xpart b.c, ypart a.n);
    currentPath := a.c .. intermediatePointA .. intermediatePointB
                   .. tension 4 .. {up}b.c;
    arrowPath(a, b, currentPath, 0.5red, true);
enddef;

%--------------------

def drawDashedLine (expr startPosition, lineVector) =
    % draws a dashed line from <startPosition> with direction
    % <lineVector>

    draw startPosition -- (startPosition + lineVector) dashed evenly;
enddef;

%--------------------

def drawDottedLine (expr startPosition, lineVector) =
    % draws a dotted line from <startPosition> with direction
    % <lineVector>

    pair endPosition;

    endPosition := startPosition + lineVector;
    draw startPosition -- endPosition dashed withdots
        withpen pencircle scaled 1.5pt;
enddef;

%--------------------

def drawLabel (expr position, alignment, size, isPlainText, st) =
    % draws text <st> at <position> with <alignment>

    if isPlainText:
        if alignment = "center":
            label(st infont defaultfont scaled size, position);
        elseif alignment = "left":
            label.lft(st infont defaultfont scaled size, position);
        elseif alignment = "right":
            label.rt(st infont defaultfont scaled size, position);
        fi
    else:
        if alignment = "center":
            label(st scaled size, position);
        elseif alignment = "left":
            label.lft(st scaled size, position);
        elseif alignment = "right":
            label.rt(st scaled size, position);
        fi
    fi
enddef;

%--------------------

def drawLine (expr startPosition, lineVector, lineWidth) =
    % draws a plain line from <startPosition> with direction
    % <lineVector> in width <lineWidth>

    pair endPosition;

    endPosition := startPosition + lineVector;
    draw startPosition -- endPosition withpen pencircle scaled lineWidth;
enddef;

%--------------------

def drawMarker (expr startPosition, markerLength, arrowLength,
                     direction) =
    % draws a marker line at <startPosition> with <markerLength> and
    % an arrow in <direction> with length <arrowLength>; the arrow is
    % positioned at half the marker length

    pair arrowStartPosition, arrowEndPosition;
    pair markerOffset, arrowOffset;

    if direction = "H":
        arrowOffset  := (arrowLength, 0);
        markerOffset := (0, markerLength);
    else:
        arrowOffset  := (0, arrowLength);
        markerOffset := (markerLength, 0);
    fi

    drawDashedLine(startPosition, markerOffset);
    arrowEndPosition   := startPosition + markerOffset / 2;
    arrowStartPosition := arrowEndPosition + arrowOffset;
    drawarrow arrowStartPosition -- arrowEndPosition;
enddef;

%--------------------

def drawMarkerPair (expr startPosition, vector, markerLength,
                         arrowLength)
                   (text direction) =
    % draws two markers at <startPosition> and <endPosition> with
    % <markerLength> and an arrow in <direction> with length
    % <arrowLength> positioned at half the marker length

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

%====================
% General Box
%====================

def Box_make (suffix shape)(expr kind, st) =
    % makes a box called <shape> with background filled with <st>

    if kind = "C":
        circleit.shape(st);
    elseif kind = "B":
        boxit.shape(st);
    else:
        boxit.shape(st);
    fi
enddef;

%--------------------

def Box_setBoxPositions (text shapeList)(expr startPosition, offset) =
    % sets center positions for shapes in <shapeList> starting at
    % <startPosition> with <offset>

    pair previousPosition;

    previousPosition := startPosition;

    forsuffixes shape = shapeList:
        shape.c = previousPosition;
        previousPosition := previousPosition + offset;
    endfor
enddef;

%--------------------

def Box_setSizeAndColor (suffix shape)(expr size, fillColor) =
    % defines size of <shape> to be <size> and fill color to be
    % <fillColor>

    shape.n - shape.w = 1/2 size;
    fill bpath.shape withcolor fillColor; 
enddef;

%=============
% Humanization
%=============
  
numeric Humanization_fontSizeFactorArrowLabel;
numeric Humanization_fontSizeFactorAxisLabel;
numeric Humanization_fontSizeFactorTitle;
numeric Humanization_fontSizeFactorNote;
numeric Humanization_measureBasePositionY;
color Humanization_measureColor;
numeric Humanization_measureLabelPositionY;
pair Humanization_measureSize;
numeric Humanization_measureTickMarkHeight;
numeric Humanization_measureTickMarkPositionY;
color Humanization_noteColor;
numeric Humanization_notePositionY;
numeric Humanization_positionArrowPositionY;
numeric Humanization_quarterWidth;
color Humanization_variationBellColorA;
color Humanization_variationBellColorB;

Humanization_fontSizeFactorArrowLabel = 0.8;
Humanization_fontSizeFactorAxisLabel  = 1.4;
Humanization_fontSizeFactorTitle      = 1.8;
Humanization_fontSizeFactorNote       = 1.2;
Humanization_measureSize = (80mm, 60mm);
Humanization_measureAxisLabelPositionY = 5mm;
Humanization_measureTickMarkPositionY = (Humanization_measureAxisLabelPositionY
                                         + 5mm);
Humanization_measureTickMarkHeight = ypart Humanization_measureSize / 20;
Humanization_positionArrowPositionY  = (Humanization_measureTickMarkPositionY
                                        + Humanization_measureTickMarkHeight
                                        + 5mm);
Humanization_measureBasePositionY  = (Humanization_positionArrowPositionY
                                      + 3mm);
Humanization_measureColor = .9 white;
Humanization_noteColor = (0.4, 0.6, 0.8);
Humanization_notePositionY = Humanization_measureBasePositionY;
Humanization_quarterWidth = xpart Humanization_measureSize / 4;
Humanization_variationBellColorA = (0.7, 0.7, 0.0);
Humanization_variationBellColorB = (0.0, 0.7, 0.0);

%--------------------

def Humanization__drawAnnotationLines (expr referencePoint,
                                            variationVector,
                                            lineVector,
                                            variationColor,
                                            st) =
    % draws dashed annotation lines for the variations starting at
    % <referencePoint> with <variationVector> for the neighboring
    % lines and the <lineVector> for the line length and also adds a
    % brace with text label <st>; <variationColor> is the color of the
    % parabola

    pair direction;
    direction := unitvector(lineVector);

    % parabola at fixed locations of dashed line
    pair offsetA, offsetB;
    pair a[];
    path p;

    offsetA := lineVector - 8mm * direction;
    offsetB := lineVector - 2mm * direction;
    a1 := referencePoint + variationVector + offsetA;
    a2 := referencePoint + offsetB;
    a3 := referencePoint - variationVector + offsetA;
    p := a1{direction} .. a2 .. {-direction}a3 -- cycle;
    draw p withcolor variationColor;
    hatchoptions(withcolor variationColor);
    hatchfill p withcolor (45, 3/2bp, -1/2bp);

    % three dashed lines
    drawDashedLine(referencePoint + variationVector, lineVector);
    drawDashedLine(referencePoint, lineVector);
    drawDashedLine(referencePoint - variationVector, lineVector);

    % brace
    pair bracePoint;
    numeric braceWidth;
    pair endPoint;
    endPoint := referencePoint + lineVector;
    braceWidth := 2mm;
    bracePoint := endPoint + braceWidth * direction;
    draw (endPoint - variationVector){direction} ... {direction}bracePoint;
    draw (endPoint + variationVector){direction} ... {direction}bracePoint;

    % text label
    numeric textOffset;
    pair textPoint;
    textOffset := 1/2 (direction dotprod urcorner st) + 2mm;
    textPoint := bracePoint + textOffset * direction;
    label(st, textPoint);
enddef;

%--------------------

def Humanization__drawMeasure (expr measureIndex,
                                    startPositionX,
                                    notePositionX,
                                    noteHeight,
                                    measureLabel,
                                    noteLabel,
                                    positionLabel) =
    % draws a measure starting at <startPositionX> where note starts
    % at <notePositionX> and has height <noteHeight> using labels
    % <measureLabel>, <noteLabel> and <positionLabel>

    numeric barLineWidth;
    numeric endPositionX;

    endPositionX = startPositionX + 4 * Humanization_quarterWidth;

    % measure
    y := Humanization_measureBasePositionY;
    Box_make(measureBox[measureIndex], "B", "");
    measureBox[measureIndex].sw = (startPositionX,
                                   Humanization_measureBasePositionY);
    Box_setSizeAndColor(measureBox[measureIndex], Humanization_measureSize,
                        Humanization_measureColor);
    drawboxed(measureBox[measureIndex]);

    % bar lines
    barLineWidth = 3pt;
    drawLine(measureBox[measureIndex].sw,
             (measureBox[measureIndex].nw - measureBox[measureIndex].sw),
             barLineWidth);
    drawLine(measureBox[measureIndex].se,
             (measureBox[measureIndex].ne - measureBox[measureIndex].se),
        barLineWidth);
    drawLabel(measureBox[measureIndex].n - (0, 4mm), "center",
              Humanization_fontSizeFactorTitle, false, measureLabel);

    for i = 0 upto 4:
        numeric x;
        pair position;
        % draw tick mark
        x = startPositionX + i * Humanization_quarterWidth;
        position := (x, Humanization_measureTickMarkPositionY);
        drawLine(position, (0, Humanization_measureTickMarkHeight), 1.5pt);
        % draw label
        position := (x, Humanization_measureAxisLabelPositionY);
        label(TEX(decimal(i/4)) scaled Humanization_fontSizeFactorAxisLabel,
              position);
    endfor

    % note
    numeric noteWidth;
    noteWidth = Humanization_quarterWidth;
    Box_make(noteBox[measureIndex], "B", "");
    noteBox[measureIndex].sw = (notePositionX, Humanization_notePositionY);
    Box_setSizeAndColor(noteBox[measureIndex], (noteWidth, noteHeight),
                        Humanization_noteColor);
    drawboxed(noteBox[measureIndex]);
    drawLabel(noteBox[measureIndex].c, "center",
              Humanization_fontSizeFactorNote, false, noteLabel);

    % position arrow
    numeric arrowLength, markerLength, totalArrowLength;
    pair startArrowPosition;
    totalArrowLength := notePositionX - startPositionX;
    startArrowPosition = (startPositionX,
                          Humanization_positionArrowPositionY);
    arrowLength := totalArrowLength / 2;
    markerLength := (Humanization_measureBasePositionY
                     - Humanization_positionArrowPositionY);
    drawMarkerPair(startArrowPosition, (totalArrowLength, 0),
                   markerLength, arrowLength, "H");
    drawLabel(startArrowPosition + (totalArrowLength / 2, -2mm),
              "center", Humanization_fontSizeFactorArrowLabel,
              false, positionLabel);
enddef;

%--------------------

def Humanization__drawVelocityInfo (expr x,
                                    noteHeight,
                                    markerIsShown,
                                    velocityLabel) =
    % draws velocity marker at position (<x>,
    % <Humanization_notePositionY>) and shows markers if
    % <markerIsShown>

    numeric arrowLength;
    numeric markerLength;
    numeric xOffset;
    numeric y;

    arrowLength = noteHeight / 3;
    y = Humanization_notePositionY;

    if markerIsShown:
        markerLength = Humanization_quarterWidth;
        xOffset = -Humanization_quarterWidth / 2;
    else:
        markerLength = 0;
        xOffset = 0;
    fi

    pair labelPosition;
    pair position;

    position = (x + xOffset, y);
    labelPosition := position + (markerLength, noteHeight) / 2;

    drawMarkerPair(position, (0, noteHeight),
                   markerLength, arrowLength, "V");
    drawLabel(labelPosition, "center",
              Humanization_fontSizeFactorArrowLabel,
              false, velocityLabel);
enddef;

%--------------------

def Humanization__hatchRectangle (expr startPoint,
                                       diagonalVector,
                                       hatchColor) =
    % hatches rectangle starting at <startPoint> with diagonal
    % <diagonalVector> in <hatchColor>

    path p;
    p := startPoint
         -- startPoint + (0, ypart diagonalVector)
         -- startPoint + diagonalVector
         -- startPoint + (xpart diagonalVector, 0)
         -- cycle;
    hatchoptions(withcolor hatchColor);
    hatchfill p withcolor (45, 3/2bp, -1/2bp);
enddef;

%--------------------

def Humanization_makeDiagram (expr measureLabel,
                                   noteLabel,
                                   positionLabelA,
                                   positionLabelB,
                                   velocityLabelA,
                                   velocityLabelB,
                                   velocityVariationLabel,
                                   timingVariationLabel) =
    % makes diagram with note transformation using labels
    % <measureLabel>, <noteLabel> and <positionLabelA>,
    % <positionLabelB>, <velocityLabelA>, <velocityLabelB>,
    % <velocityVariationLabel> and <timingVariationLabel>

    pair dashedLineVector;
    numeric secondMeasureOffset;
    numeric startPositionX;
    pair variationVector;
    numeric x;
    numeric y;

    secondMeasureOffset := 5.5 * Humanization_quarterWidth;
    startPositionX := 2mm;

    % initial measure
    numeric arrowPositionX;
    numeric originalNoteHeight;
    numeric originalNotePositionX;
    x := startPositionX;
    originalNotePositionX := x + Humanization_quarterWidth;
    originalNoteHeight := ypart Humanization_measureSize * 0.7;
    Humanization__drawMeasure(1, x, originalNotePositionX, originalNoteHeight)
                              (measureLabel)(noteLabel)(positionLabelA);
    arrowPositionX := originalNotePositionX + 1.5 * Humanization_quarterWidth;
    Humanization__drawVelocityInfo(arrowPositionX, originalNoteHeight,
                                   true, velocityLabelA);

    % transformed measure
    numeric newNoteHeight;
    numeric newNotePositionX;
    numeric scaledNoteHeight;
    numeric variation;

    x := startPositionX + secondMeasureOffset;
    newNotePositionX := x + Humanization_quarterWidth * 5/6;
    newNoteHeight := originalNoteHeight * 0.7;
    scaledNoteHeight := originalNoteHeight * 0.65;
    Humanization__drawMeasure(2, x, newNotePositionX, newNoteHeight)
                              (measureLabel)(noteLabel)(positionLabelB);
    arrowPositionX := newNotePositionX + 1.4 * Humanization_quarterWidth;
    Humanization__drawVelocityInfo(arrowPositionX, scaledNoteHeight, false,
                                   velocityLabelB);

    % velocity variation
    variation := newNoteHeight - scaledNoteHeight;
    y := Humanization_measureBasePositionY + scaledNoteHeight;
    Humanization__hatchRectangle((newNotePositionX, y),
                                 (Humanization_quarterWidth, variation),
                                 Humanization_variationBellColorA);

    % velocity annotation
    x := newNotePositionX + Humanization_quarterWidth;
    y := Humanization_notePositionY + scaledNoteHeight;
    dashedLineVector := (Humanization_quarterWidth, 0);
    variationVector = (0, originalNoteHeight * .1);
    Humanization__drawAnnotationLines((x, y), variationVector,
                                      dashedLineVector,
                                      Humanization_variationBellColorA,
                                      velocityVariationLabel);

    % timing variation
    variation := (originalNotePositionX + secondMeasureOffset
                  - newNotePositionX);
    y := Humanization_notePositionY;
    Humanization__hatchRectangle((newNotePositionX, y),
                                 (variation, newNoteHeight),
                                 Humanization_variationBellColorB);

    % timing annotation
    x := originalNotePositionX + secondMeasureOffset;
    y := Humanization_notePositionY;
    dashedLineVector := (0, originalNoteHeight);
    variationVector := (Humanization_quarterWidth * 1/4.5, 0);
    Humanization__drawAnnotationLines((x, y), variationVector,
                                      dashedLineVector,
                                      Humanization_variationBellColorB,
                                      timingVariationLabel);

    % transition arrow
    numeric arrowHeight;
    numeric arrowWidth;
    pair position;
    numeric oldAhlength;

    arrowHeight := ypart Humanization_measureSize * 0.7;
    arrowWidth  := Humanization_quarterWidth * 0.6;
    position := (startPositionX
                 + (secondMeasureOffset + 4 * Humanization_quarterWidth) / 2,
                 Humanization_measureBasePositionY
                  + ypart Humanization_measureSize / 2);
    fill position - (arrowWidth, arrowHeight) / 2
         -- position + (arrowWidth, 0) / 2
         -- position - (arrowWidth, -arrowHeight) / 2
         -- cycle withcolor black;
enddef;

%====================
% Phase Or File Boxes
%====================

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

%--------------------

def PhaseOrFileBox_setPostprocessingBoxes (expr startPosition) =
    % sets up the position and size of postprocessing phases and
    % extracts

    Box_setBoxPositions(phaseRawAudio, phaseRefinedAudio, phaseMixdown,
                        phaseFinalVideo)
                       (startPosition, PhaseOrFileBox_phaseOffsetVector);

    Box_setBoxPositions(fileRawAudio, fileRefinedAudio, fileAudio, fileVideo)
                       (phaseRawAudio.c + PhaseOrFileBox_resultOffsetVector,
                        PhaseOrFileBox_phaseOffsetVector)
enddef;

%--------------------

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

%--------------------

def PhaseOrFileBox_setPreprocessingBoxes (expr startPosition) =
    % sets up the position and size of preprocessing phases and
    % extracts

    Box_setBoxPositions(phaseExtract, phaseScore, phaseMidi, phaseSilentVideo)
                          (startPosition, PhaseOrFileBox_phaseOffsetVector);

    Box_setBoxPositions(fileExtract, fileScore, fileMidi, fileSilentVideo)
                          (phaseExtract.c + PhaseOrFileBox_resultOffsetVector,
                           PhaseOrFileBox_phaseOffsetVector);

    fileSubtitleText.c = fileSilentVideo.c
                         + (0, ypart PhaseOrFileBox_phaseOffsetVector);
enddef;

%--------------------

def PhaseOrFileBox_setPreprocessingEdges =
    % sets up the edges of preprocessing phases and extracts

    forsuffixes shape = phaseExtract, phaseScore, phaseMidi,
                        phaseSilentVideo:
      addForwardFlow(fileLilypond, shape);
    endfor

    addForwardFlow(phaseExtract,     fileExtract);
    addForwardFlow(phaseScore,       fileScore);
    addForwardFlow(phaseMidi,        fileMidi);
    addForwardFlow(phaseSilentVideo, fileSilentVideo);
    addForwardFlow(phaseSilentVideo, fileSubtitleText);
enddef;

%=================================
% Phase and File Box Configuration
%=================================

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

%==========================
% Voice and Mastering Boxes
%==========================

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

%--------------------

def MasteringBox_layoutSingleTrack (text internalShapeList)
                                   (suffix groupShape)
                                   (expr groupCenterPosition,
                                         groupShapeSize,
                                         internalShapeSize) =
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
    Box_setSizeAndColor(groupShape, groupShapeSize,
                        MasteringGroup_fillColor);
    drawboxed(groupShape);

    internalShapeCount := 3;
    internalShapeXSize := xpart internalShapeSize;
    internalShapeXOffset := ((xpart groupShapeSize) / internalShapeCount
                            - internalShapeXSize);
    firstBoxPosition := groupShape.w
                        + (internalShapeXSize + internalShapeXOffset, 0)/2;
    Box_setBoxPositions(internalShapeList)
                        (firstBoxPosition,
                         (internalShapeXSize + internalShapeXOffset, 0));

    forsuffixes shape = internalShapeList:
        Box_setSizeAndColor(shape,internalShapeSize, MasteringBox_fillColor);
        drawboxed(shape);
    endfor
enddef;

%--------------------

def MasteringBox_makeAll =
    % position all mastering boxes for voice and mastering image

    Box_make(masteringGroupA, "B", "");
    Box_make(mixerBoxA, "B",
             btex \stkB{mixdown${}_A$~by}{\tt voiceNameToAudioLevelMap} etex
             rotated 90);
    Box_make(masteringBoxA, "B",
             btex \stkB{mastering${}_A$~via}{\tt masteringCommandList} etex
             rotated 90);
    Box_make(amplificationBoxA, "B",
             btex \stkB{amplification${}_A$~by}{\tt amplificationLevel} etex
             rotated 90);
    MasteringBox_layoutSingleTrack(mixerBoxA, masteringBoxA, amplificationBoxA)
                                  (masteringGroupA,
                                   MasteringGroupA_centerPosition,
                                   MasteringGroupA_size,
                                   MasteringBoxA_size);

    Box_make(masteringGroupK, "B", "");
    Box_make(mixerBoxK, "B", btex mixdown${}_K$ etex rotated 90);
    Box_make(masteringBoxK, "B", btex mastering${}_K$ etex rotated 90);
    Box_make(amplificationBoxK, "B",
             btex amplification${}_K$ etex rotated 90);
    MasteringBox_layoutSingleTrack(mixerBoxK, masteringBoxK,
                                   amplificationBoxK)
                                  (masteringGroupK,
                                   MasteringGroupK_centerPosition,
                                   MasteringGroupK_size,
                                   MasteringBoxK_size);
    Box_make(masteringGroupDot, "B", "...");
    masteringGroupDot.c = 1/2[masteringGroupA.s, masteringGroupK.n];
    Box_setSizeAndColor(masteringGroupDot, MasteringGroupDot_size, white);
    drawunboxed(masteringGroupDot);  
enddef;

%--------------------

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

%--------------------

def VoiceAndMasteringBox_setEdges =
    % sets up the edges of postprocessing phases and extracts

    forsuffixes shape = voiceA, voiceB, voiceC:  
        addDirectFlow(shape, mixerBoxA);
        addDirectFlow(shape, mixerBoxK);
    endfor

    addForwardFlow(mixerBoxA, masteringBoxA);
    addForwardFlow(masteringBoxA, amplificationBoxA);
    addForwardFlow(amplificationBoxA, trackBoxA);
    addForwardFlow(mixerBoxK, masteringBoxK);
    addForwardFlow(masteringBoxK, amplificationBoxK);
    addForwardFlow(amplificationBoxK, trackBoxK);
enddef;

%--------------------

def VoiceAndMasteringBox_makeAll =
    % position all boxes for voice and mastering image

    VoiceBox_makeAll;
    MasteringBox_makeAll;
    TrackBox_makeAll;
    VoiceAndMasteringBox_setEdges;
enddef;

%======================================
% Voice and Mastering Box Configuration
%======================================

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
VoiceBox_offset            := ( 0mm, -20mm);
VoiceBox_size              := (25mm,  10mm);
TrackBox_size              := (30mm,  10mm);
VoiceBox_topCenterPosition := (xpart VoiceBox_size/2, 85mm);

MasteringGroupA_centerPosition := VoiceBox_topCenterPosition
                                  + (40mm + MasteringGroup_xSize/2, 5mm);
MasteringGroupK_centerPosition := (xpart MasteringGroupA_centerPosition,
                                   20mm);
TrackBox_xPosition             := xpart MasteringGroupA_centerPosition
                                  + MasteringGroup_xSize/2 + 20mm;

%====================
%====================
beginfig(1);
    color fillColor;
    pair configBoxSize;

    PhaseOrFileBox_makeAll;

    fileLilypond.w = (  0mm, 80mm);
    fileConfig.w   = ( 40mm, 15mm);
    configBoxSize := (135mm, 15mm);
    Box_setSizeAndColor(fileLilypond, PhaseOrFileBox_fileBoxSize,
                        PhaseOrFileBox_lilypondFileFillColor);
    Box_setSizeAndColor(fileConfig, configBoxSize,
                        PhaseOrFileBox_configFileFillColor);

    PhaseOrFileBox_setPreprocessingBoxes((45mm, 120mm));
    PhaseOrFileBox_setPostprocessingBoxes(phaseExtract.c + (90mm, 0mm));

    forsuffixes shape = fileExtract, fileScore, fileMidi, fileSilentVideo,
                        fileSubtitleText,
                        fileRawAudio, fileRefinedAudio, fileAudio,
                        fileVideo:
        Box_setSizeAndColor(shape, PhaseOrFileBox_fileBoxSize,
          PhaseOrFileBox_fileFillColor);
    endfor

    forsuffixes shape = phaseExtract, phaseScore, phaseMidi,
                        phaseSilentVideo, phaseRawAudio,
                        phaseRefinedAudio, phaseMixdown,
                        phaseFinalVideo:
        Box_setSizeAndColor(shape, PhaseOrFileBox_phaseBoxSize,
                            PhaseOrFileBox_phaseFillColor);
    endfor

    % --- add all edges ---
    PhaseOrFileBox_setPreprocessingEdges;
    PhaseOrFileBox_setPostprocessingEdges;

    forsuffixes shape = phaseExtract, phaseScore, phaseMidi,
                        phaseSilentVideo, phaseRawAudio,
                        phaseRefinedAudio, phaseMixdown,
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

%====================
beginfig(2);
    color fillColor;
    pair configBoxSize;

    PhaseOrFileBox_makeAll;

    fileLilypond.w = ( 0mm, 80mm);
    fileConfig.w   = (40mm, 15mm);
    configBoxSize := (50mm, 15mm);
    Box_setSizeAndColor(fileLilypond, PhaseOrFileBox_fileBoxSize,
                        PhaseOrFileBox_lilypondFileFillColor);
    Box_setSizeAndColor(fileConfig, configBoxSize,
                        PhaseOrFileBox_configFileFillColor);

    PhaseOrFileBox_setPreprocessingBoxes((45mm, 120mm));

    forsuffixes shape = fileExtract, fileScore, fileMidi,
                        fileSilentVideo, fileSubtitleText:
        Box_setSizeAndColor(shape, PhaseOrFileBox_fileBoxSize,
                            PhaseOrFileBox_fileFillColor);
    endfor

    forsuffixes shape = phaseExtract, phaseScore, phaseMidi,
                        phaseSilentVideo:
        Box_setSizeAndColor(shape, PhaseOrFileBox_phaseBoxSize,
                            PhaseOrFileBox_phaseFillColor);
    endfor

    % --- add all edges ---
    PhaseOrFileBox_setPreprocessingEdges;

    forsuffixes shape = phaseExtract, phaseScore, phaseMidi,
                        phaseSilentVideo:
        addSupport(fileConfig, shape);
    endfor

    drawboxed(fileLilypond, fileConfig,
              phaseExtract, phaseScore, phaseMidi, phaseSilentVideo,
              fileExtract, fileScore, fileMidi, fileSilentVideo,
              fileSubtitleText);
endfig;

%====================
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
                        fileRawAudio, fileRefinedAudio, fileAudio,
                        fileVideo:
        Box_setSizeAndColor(shape, PhaseOrFileBox_fileBoxSize,
                            PhaseOrFileBox_fileFillColor);
    endfor

    forsuffixes shape = phaseRawAudio, phaseRefinedAudio,
                        phaseMixdown, phaseFinalVideo:
        Box_setSizeAndColor(shape, PhaseOrFileBox_phaseBoxSize,
                            PhaseOrFileBox_phaseFillColor);
    endfor

    % --- add all edges ---
    PhaseOrFileBox_setPostprocessingEdges;

    forsuffixes shape = phaseRawAudio, phaseRefinedAudio,
                        phaseMixdown, phaseFinalVideo:
        addSupport(fileConfig, shape);
    endfor

    drawboxed(fileConfig,
              fileMidi, fileSilentVideo, fileSubtitleText,
              phaseRawAudio, phaseRefinedAudio, phaseMixdown,
              phaseFinalVideo, fileRawAudio, fileRefinedAudio,
              fileAudio, fileVideo);
endfig;

%====================
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
              true, "VIDEO TARGET");

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
    drawLabel(videoTarget.s + (0, markerLength)/2, "center",
              labelScaleFactor, true, "width");

    markerLength := ypart markerLengthVector;
    arrowLength  := xpart marginOffset / 2;
    markerPosition := videoTarget.nw + (xpart marginOffset, 0);
    drawMarkerPair(markerPosition, -marginOffset,
                   markerLength, arrowLength, "H");
    drawMarkerPair(videoTarget.ne, -marginOffset,
                   markerLength, arrowLength, "H");
    drawLabel(videoTarget.n + (0, markerLength)/2, "center",
              labelScaleFactor, true, "leftRightMargin");

    arrowLength := ypart videoTargetSize / 4;
    markerLength := xpart markerLengthVector;
    drawMarkerPair(videoTarget.se, videoTargetSize, markerLength,
                   arrowLength,  "V");
    drawLabel(videoTarget.e + (markerLength, 0)/2, "center",
              labelScaleFactor, true, "height");

    markerLength := -xpart markerLengthVector;
    arrowLength  := ypart marginOffset / 2;
    markerPosition := videoTarget.sw + (0, ypart marginOffset);
    drawMarkerPair(markerPosition, -marginOffset,
                   markerLength, arrowLength, "V");
    drawMarkerPair(videoTarget.nw, -marginOffset,
                   markerLength, arrowLength, "V");
    drawLabel(videoTarget.w, "left", labelScaleFactor,
              true, "topBottomMargin");

    markerLength := 1mm;
    arrowLength  := 2mm;
    markerPosition := 1/2[videoTarget.c, videoTarget.n];
    drawMarkerPair(markerPosition, -(1mm, 0),
                   markerLength, arrowLength, "H");
    drawLabel(markerPosition - (0, 2markerLength), "center",
              labelScaleFactor, true, "resolution")

endfig;

%====================
beginfig(5);
    VoiceAndMasteringBox_makeAll;
endfig;

%====================
beginfig(6);
    Humanization_makeDiagram(btex Takt etex,
                             btex Note etex,
                             btex Position etex,
                             btex neue Position etex,
                             btex Velocity etex,
                             btex \stkB{Velocity}{$\cdot$ Faktor} etex,
                             btex \stkB{Velocity-}{variation} etex,
                             btex \stkB{Timing-}{variation} etex);
endfig;

%====================
beginfig(7);
    Humanization_makeDiagram(btex measure etex,
                             btex note etex,
                             btex position $t_i$ etex,
                             btex $t_i + r_t\cdot(\tau(p_i)
                                  \cdot\ell\cdot adj_t)$ etex,
                             btex \stkB{velocity}{$v_i$} etex,
                             btex \stkC{velocity}{$\cdot$ factor}
                                   {$v_i \cdot \sigma(p_i)$} etex,
                             btex \stkC{velocity}{variation}
                                       {$2\cdot\psi\cdot adj_v$} etex,
                             btex \stkC{timing}{variation}
                                       {$2\cdot\tau(p_i)\cdot\ell\cdot adj_t$} etex);
endfig;

end
