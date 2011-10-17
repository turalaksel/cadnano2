#!/usr/bin/env python
# encoding: utf-8

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

from exceptions import IndexError
from operator import attrgetter
import util
from array import array
from decorators.insertion import Insertion

# import Qt stuff into the module namespace with PySide, PyQt4 independence
util.qtWrapImport('QtCore', globals(), ['pyqtSignal', 'QObject', 'Qt'])
util.qtWrapImport('QtGui', globals(), ['QUndoStack', 'QUndoCommand'])

class Strand(QObject):
    """
    A Strand is a continuous stretch of bases that are all in the same
    StrandSet (recall: a VirtualHelix is made up of two StrandSets).

    Every Strand has two endpoints. The naming convention for keeping track
    of these endpoints is based on the relative numeric value of those
    endpoints (low and high). Thus, Strand has a '_baseIdxLow', which is its
    index with the lower numeric value (typically positioned on the left),
    and a '_baseIdxHigh' which is the higher-value index (typically positioned
    on the right)

    Strands can be linked to other strands by "connections". References to
    connected strands are named "_strand5p" and "_strand3p", which correspond
    to the 5' and 3' phosphate linkages in the physical DNA strand, 
    respectively. Since Strands can point 5'-to-3' in either the low-to-high
    or high-to-low directions, connection accessor methods (connectionLow and
    connectionHigh) are bound during the init for convenience.
    """

    def __init__(self, strandSet, baseIdxLow, baseIdxHigh, oligo=None):
        super(Strand, self).__init__(strandSet)
        self._strandSet = strandSet
        self._baseIdxLow = baseIdxLow  # base index of the strand's left boundary
        self._baseIdxHigh = baseIdxHigh  # base index of the right boundary
        self._oligo = oligo
        self._strand5p = None  # 5' connection to another strand
        self._strand3p = None  # 3' connection to another strand
        self._sequence = None

        self._decorators = {}
        self._modifiers = {}

        # dynamic methods for mapping high/low connection /indices
        # to corresponding 3Prime 5Prime
        isDrawn5to3 = strandSet.isDrawn5to3()
        if isDrawn5to3:
            self.idx5Prime = self.lowIdx
            self.idx3Prime = self.highIdx
            self.connectionLow = self.connection5p
            self.connectionHigh = self.connection3p
            self.setConnectionLow = self.setConnection5p
            self.setConnectionHigh = self.setConnection3p
        else:
            self.idx5Prime = self.highIdx
            self.idx3Prime = self.lowIdx
            self.connectionLow = self.connection3p
            self.connectionHigh = self.connection5p
            self.setConnectionLow = self.setConnection3p
            self.setConnectionHigh = self.setConnection5p
        self._isDrawn5to3 = isDrawn5to3
    # end def

    def __repr__(self):
        clsName = self.__class__.__name__
        s = "%s.<%s(%s, %s)>"%(self._strandSet.__repr__(), clsName, self._baseIdxLow, self._baseIdxHigh)
        return s

    def generator3pStrand(self):
        """
        Iterate from self to the final _strand3p == None
        5prime to 3prime
        Includes originalCount to check for circular linked list
        """
        originalCount = 0
        node = self
        f = attrgetter('_strand3p')
        while node and originalCount == 0:
            yield node
            # equivalen to: node = node._strand3p
            node = f(node)
            if node == self:
                originalCount += 1
    # end def

    ### SIGNALS ###
    strandHasNewOligoSignal = pyqtSignal(QObject)
    strandDestroyedSignal = pyqtSignal(QObject)
    strandRemovedSignal = pyqtSignal(QObject)
    strandResizedSignal = pyqtSignal(QObject, tuple)
    strandXover5pChangedSignal = pyqtSignal(QObject, QObject) # strand3p, strand5p
    strandXover5pRemovedSignal = pyqtSignal(QObject, QObject) # strand3p, strand5p
    strandUpdateSignal = pyqtSignal(QObject) # strand
    strandInsertionAddedSignal = pyqtSignal(QObject, object)    # strand, insertion object
    strandInsertionChangedSignal = pyqtSignal(QObject, object)    # strand, insertion object
    strandInsertionRemovedSignal = pyqtSignal(QObject, int)     # strand, insertion index
    strandDecoratorAddedSignal = pyqtSignal(QObject, object)    # strand, decorator object
    strandDecoratorChangedSignal = pyqtSignal(QObject, object)    # strand, decorator object
    strandDecoratorRemovedSignal = pyqtSignal(QObject, int)     # strand, decorator object
    strandModifierAddedSignal = pyqtSignal(QObject, object)     # strand, modifier object
    strandModifierChangedSignal = pyqtSignal(QObject, object)     # strand, modifier object
    strandModifierRemovedSignal = pyqtSignal(QObject, int)      # strand, modifier object

    ### SLOTS ###


    ### ACCESSORS ###
    def undoStack(self):
        return self._strandSet.undoStack()

    def decorators(self):
        return self._decorators
    # end def

    def isStaple(self):
        return self._strandSet.isStaple()

    def isScaffold(self):
        return self._strandSet.isScaffold()

    def part(self):
        return self._strandSet.part()
    # end def

    def oligo(self):
        return self._oligo
    # end def

    def sequence(self):
        temp = self._sequence
        return temp if temp else ''
    # end def

    def strandSet(self):
        return self._strandSet
    # end def

    def virtualHelix(self):
        return self._strandSet.virtualHelix()
    # end def

    def setSequence(self, sequenceString):
        """
        Applies sequence string from 5' to 3'
        return the tuple (used, unused) portion of the sequenceString
        """
        if sequenceString == None:
            self._sequence = None
            return None, None
        length = self.totalLength()
        temp = sequenceString[0:length]
        # self._sequence = temp if self._isDrawn5to3 else temp[::-1]
        self._sequence = temp
        print temp
        return temp, sequenceString[length:]
    # end def

    def getPreDecoratorIdxList(self):
        """
        Return positions where predecorators should be displayed. This is
        just a very simple check for the presence of xovers on the strand.

        Will refine later by checking for lattice neighbors in 3D.
        """
        ret = range(self._baseIdxLow, self._baseIdxHigh+1)
        if self.connectionLow() != None:
            ret.remove(self._baseIdxLow)
            if self._baseIdxLow+1 in ret:
                ret.remove(self._baseIdxLow+1)
        if self.connectionHigh() != None:
            ret.remove(self._baseIdxHigh)
            if self._baseIdxHigh-1 in ret:
                ret.remove(self._baseIdxHigh-1)
        return ret
    # end def

    def setComplimentSequence(self, sequenceString, strand):
        """
        This version takes anothers strand and only sets the indices that
        align with the given complimentary strand

        return the used portion of the sequenceString

        As it depends which direction this is going, and strings are stored in
        memory left to right, we need to test for isDrawn5to3 to map the reverse
        compliment appropriately, as we traverse overlapping strands.

        We reverse the sequence ahead of time if we are applying it 5' to 3',
        otherwise we reverse the sequence post parsing if it's 3' to 5'

        Again, sequences are stored as strings in memory 5' to 3' so we need
        to jump through these hoops to iterate 5' to 3' through them correctly

        Perhaps it's wiser to merely store them left to right and reverse them
        at draw time, or export time
        """
        sLowIdx, sHighIdx = self._baseIdxLow, self._baseIdxHigh
        cLowIdx, cHighIdx = strand.idxs()

        # get the ovelap
        lowIdx, highIdx = util.overlap(sLowIdx, sHighIdx, cLowIdx, cHighIdx)

        # only get the characters we're using, while we're at it, make it the
        # reverse compliment

        totalLength = self.totalLength()
        
        # see if we are applyng 
        if sequenceString == None:
            # clear out string for in case of not total overlap
            useSeq = ''.join([' ' for x in range(totalLength)])
        else:  # use the string as is
            useSeq = sequenceString[::-1] if self._isDrawn5to3 else sequenceString

        temp = array('c', useSeq)
        if self._sequence == None:
            tempSelf = array('c', ''.join([' ' for x in range(totalLength)]) )
        else:
            tempSelf = array('c', self._sequence if self._isDrawn5to3 else self._sequence[::-1])

        # generate the index into the compliment string
        if sLowIdx < lowIdx:
            a = self.insertionLengthBetweenIdxs(sLowIdx, lowIdx-1)
        else:
            a = 0
        b = self.insertionLengthBetweenIdxs(lowIdx, highIdx)
        c = strand.insertionLengthBetweenIdxs(cLowIdx, lowIdx)
        start = lowIdx - cLowIdx + c
        end = start + b + highIdx-lowIdx +1
        tempSelf[lowIdx-sLowIdx+a:highIdx-sLowIdx+1 + a+ b] = temp[start:end]
        self._sequence = tempSelf.tostring()

        # if we need to reverse it do it now
        if not self._isDrawn5to3:
            self._sequence = self._sequence[::-1]

        # test to see if the string is empty(), annoyingly expensive
        if len(self._sequence.strip()) == 0:
            self._sequence = None
        print self._sequence, totalLength, "comp"
        return self._sequence
    # end def

    ### PUBLIC METHODS FOR QUERYING THE MODEL ###
    def connection3p(self):
        return self._strand3p
    # end def

    def connection5p(self):
        return self._strand5p
    # end def

    def idxs(self):
        return (self._baseIdxLow, self._baseIdxHigh)
    # end def
    
    def updateIdxs(self, delta):
        self._baseIdxLow += delta
        self._baseIdxHigh) += delta
    # end def

    def lowIdx(self):
        return self._baseIdxLow
    # end def

    def highIdx(self):
        return self._baseIdxHigh
    # end def

    def idx3Prime(self):
        """docstring for idx3Prime"""
        return self.idx3Prime

    def idx5Prime(self):
        """docstring for idx3Prime"""
        return self.idx5Prime

    def isDrawn5to3(self):
        return self._strandSet.isDrawn5to3()
    # end def

    def length(self):
        return self._baseIdxHigh - self._baseIdxLow + 1
    # end def
    
    def insertionsOnStrand(self, idxL=None, idxH=None):
        """
        if passed indices it will use those as a bounds
        """
        insertions = []
        coord = self.virtualHelix().coord()
        insertionsDict = self.part().insertions()[coord]
        sortedIndices = sorted(insertionsDict.keys())
        if idxL == None:
            idxL, idxH = self.idxs()
        for index in sortedIndices:
            insertion = insertionsDict[index]
            if idxL <= insertion.idx() <= idxH:
                insertions.append(insertion)
            # end if
        # end for
        return insertions
    # end def
    
    def totalLength(self):
        """
        includes the length of insertions in addition to the bases
        """
        tL = 0
        insertions = self.insertionsOnStrand()
        
        for insertion in insertions:
            tL += insertion.length()
        return tL + self.length()
    # end def
    
    def insertionLengthBetweenIdxs(self, idxL, idxH):
        """
        includes the length of insertions in addition to the bases
        """
        tL = 0
        insertions = self.insertionsOnStrand(idxL, idxH)
        for insertion in insertions:
            tL += insertion.length()
        return tL
    # end def

    def getSequenceList(self):
        """
        return the list of sequences strings comprising the sequence and the
        inserts as a tuple with the index of the insertion
        [(idx, (strandItemString, insertionItemString), ...]
        
        This takes advantage of the fact the python iterates a dictionary
        by keys in order so if keys are indices, the insertions will iterate out
        from low index to high index 
        """
        seqList = []
        isDrawn5to3 = self._isDrawn5to3
        seq = self._sequence if isDrawn5to3 else self._sequence[::-1]
        # assumes a sequence has been applied correctly and is up to date
        tL = self.totalLength()

        offsetLast = 0
        lengthSoFar = 0
        iLength = 0
        lI, hI = self.idxs()
        
        for insertion in self.insertionsOnStrand():
            iLength = insertion.length()
            index = insertion.idx()
            offset = index + 1 - lI + lengthSoFar
            if iLength < 0:
                offset -= 1
            # end if
            lengthSoFar += iLength
            seqItem = seq[offsetLast:offset] # the stranditem seq
            
            # Because skips literally skip displaying a character at a base
            # position, this needs to be accounted for seperately
            if iLength < 0:
                seqItem += ' '
                offsetLast = offset
            else:
                offsetLast = offset + iLength
            seqInsertion = seq[offset:offsetLast] # the insertions sequence
            seqList.append((index, (seqItem, seqInsertion)))
        # end for
        # append the last bit of the strand
        seqList.append((lI+tL, (seq[offsetLast:tL],'')))
        print seqList
        if not isDrawn5to3:
            # reverse it again so all sub sequences are from 5' to 3'
            for i in range(len(seqList)):
                index, temp = seqList[i]
                seqList[i] = (index, (temp[0][::-1], temp[1][::-1]) )
        return seqList
    # end def
        

    def hasXoverAt(self, idx):
        """
        An xover is necessarily at an enpoint of a strand
        """
        if idx == self.highIdx():
            return True if self.connectionHigh() != None else False
        elif idx == self.lowIdx():
            return True if self.connectionLow() != None else False
        else:
            return False
    # end def

    def getResizeBounds(self, idx):
        """
        Determines (inclusive) low and high drag boundaries resizing
        from an endpoint located at idx.

        When resizing from _baseIdxLow:
            low bound is determined by checking for lower neighbor strands.
            high bound is the index of this strand's high cap, minus 1.

        When resizing from _baseIdxHigh:
            low bound is the index of this strand's low cap, plus 1.
            high bound is determined by checking for higher neighbor strands.

        When a neighbor is not present, just use the Part boundary.
        """
        neighbors = self._strandSet.getNeighbors(self)
        if idx == self._baseIdxLow:
            if neighbors[0]:
                low = neighbors[0].highIdx()+1
            else:
                low = self.part().minBaseIdx()
            return low, self._baseIdxHigh-1
        else:  # self._baseIdxHigh
            if neighbors[1]:
                high = neighbors[1].lowIdx()-1
            else:
                high = self.part().maxBaseIdx()
            return self._baseIdxLow+1, high
    # end def

    ### PUBLIC METHODS FOR EDITING THE MODEL ###
    def setConnection3p(self, strand):
        self._strand3p = strand
    # end def

    def setConnection5p(self, strand):
        self._strand5p = strand
    # end def

    # def setConnectionLow(self):
    #     """Gets bound to setConnection5p or setConnection3p in __init__."""
    #     pass
    # 
    # def setConnectionHigh(self):
    #     """Gets bound to setConnection5p or setConnection3p in __init__."""
    #     pass

    def setIdxs(self, idxs):
        self._baseIdxLow = idxs[0]
        self._baseIdxHigh = idxs[1]
    # end def

    def setStrandSet(self, strandSet):
        self._strandSet = strandSet
    # end def

    def setOligo(self, newOligo, emitSignal=True):
        self._oligo = newOligo
        if emitSignal:
            self.strandHasNewOligoSignal.emit(self)
    # end def

    def addDecorators(self, additionalDecorators):
        """Used to add decorators during a merge operation."""
        self._decorators.update(additionalDecorators)
    # end def

    def split(self, idx):
        """Called by view items to split this strand at idx."""
        self._strandSet.splitStrand(self, idx)

    def destroy(self):
        self.setParent(None)
        self.deleteLater()  # QObject also emits a destroyed() Signal
    # end def

    def resize(self, newIdxs, useUndoStack=True):
        c = Strand.ResizeCommand(self, newIdxs)
        util.execCommandList(self, [c], desc="Resize strand", useUndoStack=useUndoStack)
    # end def

    def merge(self, idx):
        """Check for neighbor."""
        lowNeighbor, highNeighbor = self._strandSet.getNeighbors(self)
        # determine where to check for neighboring endpoint
        if idx == self._baseIdxLow:
            if lowNeighbor:
                if lowNeighbor.highIdx() == idx - 1:
                    self._strandSet.mergeStrands(self, lowNeighbor)
        elif idx == self._baseIdxHigh:
            if highNeighbor:
                if highNeighbor.lowIdx() == idx + 1:
                    self._strandSet.mergeStrands(self, highNeighbor)
        else:
            raise IndexError
    # end def

    def addInsertion(self, idx, length, useUndoStack=True):
        """
        Adds an insertion or skip at idx.
        length should be
            >0 for an insertion
            -1 for a skip
        """
        idxLow, idxHigh = self.idxs()
        if idxLow <= idx <= idxHigh:
            if not self.hasInsertionAt(idx):
                # make sure length is -1 if a skip
                if length < 0:
                    length = -1
                c = Strand.AddInsertionCommand(self, idx, length)
                util.execCommandList(self, [c], desc="Add Insertion", useUndoStack=useUndoStack)
            # end if
        # end if
    # end def

    def removeInsertion(self,  idx, useUndoStack=True):
        idxLow, idxHigh = self.idxs()
        if idxLow <= idx <= idxHigh:
            if self.hasInsertionAt(idx):
                c = Strand.RemoveInsertionCommand(self, idx)
                util.execCommandList(self, [c], desc="Remove Insertion", useUndoStack=useUndoStack)
            # end if
        # end if
    # end def

    def changeInsertion(self, idx, length, useUndoStack=True):
        idxLow, idxHigh = self.idxs()
        if idxLow <= idx <= idxHigh:
            if self.hasInsertionAt(idx):
                if length == 0:
                    self.removeInsertion(idx)
                else:
                    # make sure length is -1 if a skip
                    if length < 0:
                        length = -1
                    c = Strand.ChangeInsertionCommand(self, idx, length)
                    util.execCommandList(self, [c], desc="Change Insertion", useUndoStack=useUndoStack)
            # end if
        # end if
    # end def

    ### PUBLIC SUPPORT METHODS ###
    def hasInsertionAt(self, idx):
        coord = self.virtualHelix().coord()
        insts = self.part().insertions()[coord]
        return idx in insts
    # end def

    def hasConnection3p(self):
        if self._strand3p != None:
            return True
        return False

    def hasConnection5p(self):
        if self._strand5p != None:
            return True
        return False

    def hasDecoratorAt(self, idx):
        return idx in self._decorators
    # end def

    def hasModifierAt(self, idx):
        return idx in self._modifiers
    # end def

    def getRemoveInsertionCommandsAfterSplit(self):
        """
        Called by StrandSet's SplitCommand after copying the strand to be
        split. Either copy could have extra decorators that the copy should
        not retain.

        Removes Insertions, Decorators, and Modifiers

        Problably want to wrap with a macro
        """
        coord = self.virtualHelix().coord()
        insts = self.part().insertions()[coord]
        decs = self._decorators
        mods = self._modifiers
        idxMin, idxMax = self.idxs()
        commands = []
        for key in insts:
            if key > idxMax or key < idxMin:
                print "removing %s insertion at %d" % (self, key)
                commands.append(Strand.RemoveInsertionCommand(self, key))
            #end if
            else:
                print "keeping %s insertion at %d" % (self, key)
        # end for
        """
        ADD CODE HERE TO HANDLE DECORATORS AND MODIFIERS
        """
        return commands
        # util.execCommandList(self, cList, desc="Remove Insertions", useUndoStack=True)
    # end def

    def copy(self):
        pass
    # end def

    def shallowCopy(self):
        """
        can't use python module 'copy' as the dictionary _decorators
        needs to be shallow copied as well, but wouldn't be if copy.copy()
        is used, and copy.deepcopy is undesired
        """
        nS = Strand(self._strandSet, *self.idxs())
        nS._oligo = self._oligo
        nS._strand5p = self._strand5p
        nS._strand3p = self._strand3p
        # required to shallow copy the dictionary
        nS._decorators = dict(self._decorators.items())
        nS._sequence = None# self._sequence
        return nS
    # end def

    def deepCopy(self, strandSet, oligo):
        """
        can't use python module 'copy' as the dictionary _decorators
        needs to be shallow copied as well, but wouldn't be if copy.copy()
        is used, and copy.deepcopy is undesired
        """
        nS = Strand(strandSet, *self.idxs())
        nS._oligo = oligo
        decs = nS._decorators
        for key, decOrig in self._decorators:
            decs[key] = decOrig.deepCopy()
        # end fo
        nS._sequence = self._sequence
        return nS
    # end def

    ### COMMANDS ###
    class ResizeCommand(QUndoCommand):
        def __init__(self, strand, newIdxs):
            super(Strand.ResizeCommand, self).__init__()
            self.strand = strand
            self.oldIndices = strand.idxs()
            self.newIdxs = newIdxs
        # end def

        def redo(self):
            std = self.strand
            nI = self.newIdxs
            strandSet = self.strand.strandSet()
            part = strandSet.part()

            std.setIdxs(nI)
            std.strandResizedSignal.emit(std, nI)

            # for updating the Slice View displayed helices
            part.partStrandChangedSignal.emit(strandSet.virtualHelix())
        # end def

        def undo(self):
            std = self.strand
            oI = self.oldIndices
            strandSet = self.strand.strandSet()
            part = strandSet.part()

            std.setIdxs(oI)
            std.strandResizedSignal.emit(std, oI)

            # for updating the Slice View displayed helices
            part.partStrandChangedSignal.emit(strandSet.virtualHelix())
        # end def
    # end class

    class AddInsertionCommand(QUndoCommand):
        def __init__(self, strand, idx, length):
            super(Strand.AddInsertionCommand, self).__init__()
            self._strand = strand
            coord = strand.virtualHelix().coord()
            self._insertions = strand.part().insertions()[coord]
            self._idx = idx
            self._length = length
            self._insertion = Insertion(idx, length)
        # end def

        def redo(self):
            strand = self._strand
            inst = self._insertion
            self._insertions[self._idx] = inst
            strand.strandInsertionAddedSignal.emit(strand, inst)
        # end def

        def undo(self):
            strand = self._strand
            idx = self._idx
            del self._insertions[idx]
            strand.strandInsertionRemovedSignal.emit(strand, idx)
        # end def
    # end class

    class RemoveInsertionCommand(QUndoCommand):
        def __init__(self, strand, idx):
            super(Strand.RemoveInsertionCommand, self).__init__()
            self._strand = strand
            self._idx = idx
            coord = strand.virtualHelix().coord()
            self._insertions = strand.part().insertions()[coord]
            self._insertion = self._insertions[idx]
        # end def

        def redo(self):
            strand = self._strand
            coord = strand.virtualHelix().coord()
            idx = self._idx
            del self._insertions[idx]
            strand.strandInsertionRemovedSignal.emit(strand, idx)
        # end def

        def undo(self):
            strand = self._strand
            coord = strand.virtualHelix().coord()
            inst = self._insertion
            self._insertions[self._idx] = inst
            strand.strandInsertionAddedSignal.emit(strand, inst)
        # end def
    # end class

    class ChangeInsertionCommand(QUndoCommand):
        """
        Changes the length of an insertion to a non-zero value
        the caller of this needs to handle the case where a zero length
        is required and call RemoveInsertionCommand
        """
        def __init__(self, strand, idx, newLength):
            super(Strand.ChangeInsertionCommand, self).__init__()
            self._strand = strand
            coord = strand.virtualHelix().coord()
            self._insertions = strand.part().insertions()[coord]
            self._idx = idx
            self._newLength = newLength
            self._oldLength = self._insertions[idx].length()
        # end def

        def redo(self):
            strand = self._strand
            inst = self._insertions[self._idx]
            inst.setLength(self._newLength)
            strand.strandInsertionChangedSignal.emit(strand, inst)
        # end def

        def undo(self):
            strand = self._strand
            inst = self._insertions[self._idx]
            inst.setLength(self._oldLength)
            strand.strandInsertionChangedSignal.emit(strand, inst)
        # end def
    # end class
# end class
