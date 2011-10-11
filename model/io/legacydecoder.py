# The MIT License
#
# Copyright (c) 2011 Wyss Institute at Harvard University
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# http://www.opensource.org/licenses/mit-license.php

# from cadnano import app
from model.document import Document
from model.enum import LatticeType, StrandType
from model.parts.honeycombpart import HoneycombPart
from model.parts.squarepart import SquarePart
from model.virtualhelix import VirtualHelix
from ui.dialogs.ui_latticetype import Ui_LatticeType
import util
# import Qt stuff into the module namespace with PySide, PyQt4 independence
util.qtWrapImport('QtGui', globals(),  ['qApp', 'QColor', 'QDialog', 'QDialogButtonBox'])

NODETAG = "node"
NAME = "name"
OBJ_ID = "objectid"
INST_ID = "instanceid"
DONE = "done"
CHECKED = "check"
LOCKED = "locked"

VHELIX = "vhelix"
NUM = "num"
COL = "col"
ROW = "row"
SCAFFOLD = "scaffold"
STAPLE = "staple"
INSERTION = "insertion"
DELETION = "deletion"

def doc_from_legacy_dict(obj):
    """
    Takes a loaded legacy dictionary, returns a loaded Document
    """
    numBases = len(obj['vstrands'][0]['scaf'])
    dialog = QDialog()
    dialogLT = Ui_LatticeType()
    dialogLT.setupUi(dialog)

    # determine lattice type
    if numBases % 21 == 0 and numBases % 32 == 0:
        if dialog.exec_() == 1:
            latticeType = LatticeType.Square
        else:
            latticeType = LatticeType.Honeycomb
    elif numBases % 32 == 0:
        latticeType = LatticeType.Square
    elif numBases % 21 == 0:
        latticeType = LatticeType.Honeycomb
    else:
        if dialog.exec_() == 1:
            latticeType = LatticeType.Square
        else:
            latticeType = LatticeType.Honeycomb

    doc = Document()

    # create part according to lattice type
    if latticeType == LatticeType.Honeycomb:
        steps = numBases/21
        part = HoneycombPart(document=doc, maxRow=30, maxCol=32, maxSteps=steps)
    elif latticeType == LatticeType.Square:
        part = doc.addSquarePart()
        isSQ100 = True  # check for custom SQ100 format
        for helix in obj['vstrands']:
            if helix['col'] != 0:
                isSQ100 = False
                break
        if isSQ100:
            dialogLT.label.setText("Is this a SQ100 file?")
            if dialog.exec_() == 1:
                numRows, numCols = 100, 1
            else:
                numRows, numCols = 30, 30
        else:
            numRows, numCols = 30, 30
        steps = numBases/32
        part = SquarePart(document=doc, maxRow=30, maxCol=30, maxSteps=steps)
    else:
        raise TypeError("Lattice type not recognized")

    doc._addPart(part)
    # part.setDimensions((numRows, numCols, numBases))
    # part.setName(obj["name"])

    for helix in obj['vstrands']:
        row = helix['row']
        col = helix['col']
        scaf= helix['scaf']
        part.createVirtualHelix(row, col, useUndoStack=False)

    # helixNo, numHelixes = -1, len(obj['vstrands'])-1
    # 
    # scaf_seg = defaultdict(list)
    # scaf_xo = defaultdict(list)
    # stap_seg = defaultdict(list)
    # stap_xo = defaultdict(list)
    # 
    # try:
    #     for helix in obj['vstrands']:
    #         helixNo += 1
    #         # print "helix %i/%i (%i%%)"%(helixNo, numHelixes, helixNo*100/numHelixes)
    #         vhNum = helix['num']
    #         vh = part.getVirtualHelix(vhNum)
    #         scaf = helix['scaf']
    #         stap = helix['stap']
    #         inserts = helix['loop']
    #         skips = helix['skip']
    #         assert(len(scaf)==len(stap) and len(stap)==vh.numBases() and\
    #                len(scaf)==len(inserts) and len(inserts)==len(skips))
    #         # read scaffold segments and xovers
    #         for i in range(len(scaf)):
    #             fiveVH, fiveIdx, threeVH, threeIdx = scaf[i]
    #             if fiveVH == -1 and threeVH == -1:
    #                 continue  # null base
    #             if isSegmentStartOrEnd(StrandType.Scaffold, vhNum, i, fiveVH,\
    #                                    fiveIdx, threeVH, threeIdx):
    #                 scaf_seg[vhNum].append(i)
    #             if fiveVH != vhNum and threeVH != vhNum:  # special case
    #                 scaf_seg[vhNum].append(i)  # end segment on a double crossover
    #             if is3primeXover(StrandType.Scaffold, vhNum, i, threeVH, threeIdx):
    #                 scaf_xo[vhNum].append((i, threeVH, threeIdx))
    #         assert (len(scaf_seg[vhNum]) % 2 == 0)
    #         # install scaffold segments
    #         for i in range(0, len(scaf_seg[vhNum]), 2):
    #             if vhNum % 2 == 0:
    #                 startIdx, endIdx = scaf_seg[vhNum][i], scaf_seg[vhNum][i+1]
    #             else:
    #                 endIdx, startIdx = scaf_seg[vhNum][i], scaf_seg[vhNum][i+1]
    #             vh.connectStrand(StrandType.Scaffold, startIdx, endIdx,\
    #                              useUndoStack=False, police=False, speedy=True)
    #         # read staple segments and xovers
    #         for i in range(len(stap)):
    #             fiveVH, fiveIdx, threeVH, threeIdx = stap[i]
    #             if fiveVH == -1 and threeVH == -1:
    #                 continue  # null base
    #             if isSegmentStartOrEnd(StrandType.Staple, vhNum, i, fiveVH,\
    #                                    fiveIdx, threeVH, threeIdx):
    #                 stap_seg[vhNum].append(i)
    #             if fiveVH != vhNum and threeVH != vhNum:  # special case
    #                 stap_seg[vhNum].append(i)  # end segment on a double crossover
    #             if is3primeXover(StrandType.Staple, vhNum, i, threeVH, threeIdx):
    #                 stap_xo[vhNum].append((i, threeVH, threeIdx))
    #         assert (len(stap_seg[vhNum]) % 2 == 0)
    #         # install staple segments
    #         for i in range(0, len(stap_seg[vhNum]), 2):
    #             if vhNum % 2 == 0:
    #                 startIdx, endIdx = stap_seg[vhNum][i], stap_seg[vhNum][i+1]
    #             else:
    #                 endIdx, startIdx = stap_seg[vhNum][i], stap_seg[vhNum][i+1]
    #             vh.connectStrand(StrandType.Staple, startIdx, endIdx,\
    #                              useUndoStack=False, police=False,\
    #                              color=QColor(136, 136, 136), speedy=True)
    # except AssertionError:
    #     dialogLT.label.setText("Unrecognized file format.")
    #     dialogLT.buttonBox.setStandardButtons(QDialogButtonBox.Ok)
    #     dialog.exec_()
    # 
    # helixNo = -1
    # for helix in obj['vstrands']:
    #     helixNo += 1
    #     # print "xo %i/%i (%i%%)"%(helixNo, numHelixes, helixNo*100/numHelixes)
    #     vhNum = helix['num']
    #     vh = part.getVirtualHelix(vhNum)
    #     scaf = helix['scaf']
    #     stap = helix['stap']
    #     inserts = helix['loop']
    #     skips = helix['skip']
    #     # install scaffold xovers
    #     for (idx, threeVH, threeIdx) in scaf_xo[vhNum]:
    #         threeVH = part.getVirtualHelix(threeVH)
    #         vh.installXoverFrom3To5(StrandType.Scaffold, idx, threeVH,\
    #                         threeIdx, useUndoStack=False, speedy=True, police=False)
    #     # install staple xovers
    #     for (idx, threeVH, threeIdx) in stap_xo[vhNum]:
    #         threeVH = part.getVirtualHelix(threeVH)
    #         vh.installXoverFrom3To5(StrandType.Staple, idx, threeVH,\
    #                         threeIdx, useUndoStack=False, speedy=True, police=False)
    # helixNo = -1
    # for helix in obj['vstrands']:
    #     helixNo += 1
    #     # print "loop/col %i/%i (%i%%)"%(helixNo, numHelixes, helixNo*100/numHelixes)
    #     vhNum = helix['num']
    #     vh = part.getVirtualHelix(vhNum)
    #     scaf = helix['scaf']
    #     stap = helix['stap']
    #     inserts = helix['loop']
    #     skips = helix['skip']
    #     # populate colors, inserts, and skips
    #     for baseIdx, colorNumber in helix['stap_colors']:
    #         color = QColor((colorNumber>>16)&0xFF, (colorNumber>>8)&0xFF, colorNumber&0xFF)
    #         vh.applyColorAt(color, StrandType.Staple, baseIdx, useUndoStack=False)
    #     for i in range(len(stap)):
    #         sumOfInsertSkip = inserts[i] + skips[i]
    #         if sumOfInsertSkip != 0:
    #             vh.installInsert(StrandType.Scaffold, i, sumOfInsertSkip,\
    #                            useUndoStack=False, speedy=True)
    # # part.updateAcyclicLengths()
    return doc

def isSegmentStartOrEnd(strandType, vhNum, baseIdx, fiveVH, fiveIdx, threeVH, threeIdx):
    """Returns True if the base is a breakpoint or crossover."""
    if strandType == StrandType.Scaffold:
        offset = 1
    else:
        offset = -1
    if (fiveVH == vhNum and threeVH != vhNum):
        return True
    if (fiveVH != vhNum and threeVH == vhNum):
        return True
    if (vhNum % 2 == 0 and fiveVH == vhNum and fiveIdx != baseIdx-offset):
        return True
    if (vhNum % 2 == 0 and threeVH == vhNum and threeIdx != baseIdx+offset):
        return True
    if (vhNum % 2 == 1 and fiveVH == vhNum and fiveIdx != baseIdx+offset):
        return True
    if (vhNum % 2 == 1 and threeVH == vhNum and threeIdx != baseIdx-offset):
        return True
    if (fiveVH == -1 and threeVH != -1):
        return True
    if (fiveVH != -1 and threeVH == -1):
        return True
    return False

def is3primeXover(strandType, vhNum, baseIdx, threeVH, threeIdx):
    """Returns True of the threeVH doesn't match vhNum, or threeIdx
    is not a natural neighbor of baseIdx."""
    if threeVH == -1:
        return False
    if vhNum != threeVH:
        return True
    if strandType == StrandType.Scaffold:
        offset = 1
    else:
        offset = -1
    if (vhNum % 2 == 0 and threeVH == vhNum and threeIdx != baseIdx+offset):
        return True
    if (vhNum % 2 == 1 and threeVH == vhNum and threeIdx != baseIdx-offset):
        return True
    return False
