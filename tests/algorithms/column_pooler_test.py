# ----------------------------------------------------------------------
# Numenta Platform for Intelligent Computing (NuPIC)
# Copyright (C) 2016, Numenta, Inc.  Unless you have an agreement
# with Numenta, Inc., for a separate license for this software code, the
# following terms and conditions apply:
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero Public License version 3 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU Affero Public License for more details.
#
# You should have received a copy of the GNU Affero Public License
# along with this program.  If not, see http://www.gnu.org/licenses.
#
# http://numenta.org/licenses/
# ----------------------------------------------------------------------

import unittest
import numpy as np

from nupic.data.generators.pattern_machine import PatternMachine
from nupic.research.monitor_mixin.temporal_memory_monitor_mixin import (
  TemporalMemoryMonitorMixin
)
from htmresearch.algorithms.column_pooler import ColumnPooler



class MonitoredColumnPooler(TemporalMemoryMonitorMixin, ColumnPooler):
  pass



class ExtensiveColumnPoolerTest(unittest.TestCase):
  """
  Algorithmic tests for the ColumnPooler region.

  Each test actually tests multiple aspects of the algorithm. For more
  atomic tests refer to column_pooler_unit_test.

  The notation for objects is the following:
    object{patternA, patternB, ...}

  In these tests, the proximally-fed SDR's are simulated as unique (location,
  feature) pairs regardless of actual locations and features, unless stated
  otherwise.
  """

  inputWidth = 2048 * 8
  numInputActiveBits = int(0.02 * inputWidth)
  outputWidth = 2048
  numOutputActiveBits = 40
  seed = 42


  def testNewInputs(self):
    """
    Checks that the behavior is correct when facing unseed inputs.
    """
    self.init()

    # feed the first input, a random SDR should be generated
    initialPattern = self.generateObject(1)
    self.learn(initialPattern, numRepetitions=1, newObject=True)
    representation = self._getActiveRepresentation()
    self.assertEqual(
      len(representation),
      self.numOutputActiveBits,
      "The generated representation is incorrect"
    )

    # feed a new input for the same object, the previous SDR should persist
    newPattern = self.generateObject(1)
    self.learn(newPattern, numRepetitions=1, newObject=False)
    newRepresentation = self._getActiveRepresentation()
    self.assertNotEqual(initialPattern, newPattern)
    self.assertEqual(
      newRepresentation,
      representation,
      "The SDR did not persist when learning the same object"
    )

    # without sensory input, the SDR should persist as well
    emptyPattern = [set()]
    self.learn(emptyPattern, numRepetitions=1, newObject=False)
    newRepresentation = self._getActiveRepresentation()
    self.assertEqual(
      newRepresentation,
      representation,
      "The SDR did not persist after an empty input."
    )


  def testLearnSinglePattern(self):
    """
    A single pattern is learnt for a single object.
    Objects: A{X, Y}
    """
    self.init()

    object = self.generateObject(1)
    self.learn(object, numRepetitions=1, newObject=True)
    # check that the active representation is sparse
    representation = self._getActiveRepresentation()
    self.assertEqual(
      len(representation),
      self.numOutputActiveBits,
      "The generated representation is incorrect"
    )

    # check that the pattern was correctly learnt
    self.infer(feedforwardPattern=object[0])
    self.assertEqual(
      self._getActiveRepresentation(),
      representation,
      "The pooled representation is not stable"
    )

    # present new pattern for same object
    # it should be mapped to the same representation
    newPattern = [self.generatePattern()]
    self.learn(newPattern, numRepetitions=1, newObject=False)
    # check that the active representation is sparse
    newRepresentation = self._getActiveRepresentation()
    self.assertEqual(
      newRepresentation,
      representation,
      "The new pattern did not map to the same object representation"
    )

    # check that the pattern was correctly learnt and is stable
    self.infer(feedforwardPattern=object[0])
    self.assertEqual(
      self._getActiveRepresentation(),
      representation,
      "The pooled representation is not stable"
    )


  def testLearnSingleObject(self):
    """
    Many patterns are learnt for a single object.
    Objects: A{P, Q, R, S, T}
    """
    self.init()

    object = self.generateObject(numPatterns=5)
    self.learn(object, numRepetitions=1, randomOrder=True, newObject=True)
    representation = self._getActiveRepresentation()

    # check that all patterns map to the same object
    for pattern in object:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representation,
        "The pooled representation is not stable"
      )

    # if activity stops, check that the representation persists
    self.infer(feedforwardPattern=set())
    self.assertEqual(
      self._getActiveRepresentation(),
      representation,
      "The pooled representation did not persist"
    )


  def testLearnTwoObjectNoCommonPattern(self):
    """
    Same test as before, using two objects, without common pattern.
    Objects: A{P, Q, R, S,T}   B{V, W, X, Y, Z}
    """
    self.init()

    objectA = self.generateObject(numPatterns=5)
    self.learn(objectA, numRepetitions=1, randomOrder=True, newObject=True)
    representationA = self._getActiveRepresentation()

    objectB = self.generateObject(numPatterns=5)
    self.learn(objectB, numRepetitions=1, randomOrder=True, newObject=True)
    representationB = self._getActiveRepresentation()

    self.assertNotEqual(representationA, representationB)

    # check that all patterns map to the same object
    for pattern in objectA:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationA,
        "The pooled representation for the first object is not stable"
      )

    # check that all patterns map to the same object
    for pattern in objectB:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationB,
        "The pooled representation for the second object is not stable"
      )

    # feed union of patterns in object A
    pattern = objectA[0] | objectA[1]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA,
      "The active representation is incorrect"
    )

    # feed unions of patterns in objects A and B
    pattern = objectA[0] | objectB[0]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA | representationB,
      "The active representation is incorrect"
    )



  def testLearnTwoObjectsOneCommonPattern(self):
    """
    Same test as before, except the two objects share a pattern
    Objects: A{P, Q, R, S,T}   B{P, W, X, Y, Z}
    """
    self.init()

    objectA = self.generateObject(numPatterns=5)
    self.learn(objectA, numRepetitions=1, randomOrder=True, newObject=True)
    representationA = self._getActiveRepresentation()

    objectB = self.generateObject(numPatterns=5)
    objectB[0] = objectA[0]
    self.learn(objectB, numRepetitions=1, randomOrder=True, newObject=True)
    representationB = self._getActiveRepresentation()

    self.assertNotEqual(representationA, representationB)
    # very small overlap
    self.assertLessEqual(len(representationA & representationB), 3)

    # check that all patterns except the common one map to the same object
    for pattern in objectA[1:]:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationA,
        "The pooled representation for the first object is not stable"
      )

    # check that all patterns except the common one map to the same object
    for pattern in objectB[1:]:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationB,
        "The pooled representation for the second object is not stable"
      )

    # feed shared pattern
    pattern = objectA[0]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA | representationB,
      "The active representation is incorrect"
    )

    # feed union of patterns in object A
    pattern = objectA[1] | objectA[2]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA,
      "The active representation is incorrect"
    )

    # feed unions of patterns in objects A and B
    pattern = objectA[1] | objectB[1]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA | representationB,
      "The active representation is incorrect"
    )

  def testLearnThreeObjectsOneCommonPattern(self):
    """
    Same test as before, with three objects
    Objects: A{P, Q, R, S,T}   B{P, W, X, Y, Z}   C{W, H, I, K, L}
    """
    self.init()

    objectA = self.generateObject(numPatterns=5)
    self.learn(objectA, numRepetitions=1, randomOrder=True, newObject=True)
    representationA = self._getActiveRepresentation()

    objectB = self.generateObject(numPatterns=5)
    objectB[0] = objectA[0]
    self.learn(objectB, numRepetitions=1, randomOrder=True, newObject=True)
    representationB = self._getActiveRepresentation()

    objectC = self.generateObject(numPatterns=5)
    objectC[0] = objectB[1]
    self.learn(objectC, numRepetitions=1, randomOrder=True, newObject=True)
    representationC = self._getActiveRepresentation()

    self.assertNotEquals(representationA, representationB, representationC)
    # very small overlap
    self.assertLessEqual(len(representationA & representationB), 3)
    self.assertLessEqual(len(representationB & representationC), 3)
    self.assertLessEqual(len(representationA & representationC), 3)


    # check that all patterns except the common one map to the same object
    for pattern in objectA[1:]:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationA,
        "The pooled representation for the first object is not stable"
      )

    # check that all patterns except the common one map to the same object
    for pattern in objectB[2:]:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationB,
        "The pooled representation for the second object is not stable"
      )

    # check that all patterns except the common one map to the same object
    for pattern in objectC[1:]:
      self.infer(feedforwardPattern=pattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationC,
        "The pooled representation for the third object is not stable"
      )

    # feed shared pattern between A and B
    pattern = objectA[0]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA | representationB,
      "The active representation is incorrect"
    )

    # feed shared pattern between B and C
    pattern = objectB[1]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationB | representationC,
      "The active representation is incorrect"
    )

    # feed union of patterns in object A
    pattern = objectA[1] | objectA[2]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA,
      "The active representation is incorrect"
    )

    # feed unions of patterns to activate all objects
    pattern = objectA[1] | objectB[1]
    self.infer(feedforwardPattern=pattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA | representationB | representationC,
      "The active representation is incorrect"
    )


  def testLearnThreeObjectsOneCommonPatternSpatialNoise(self):
    """
    Same test as before, with three objects
    Objects: A{P, Q, R, S,T}   B{P, W, X, Y, Z}   C{W, H, I, K, L}
    """
    self.init()

    objectA = self.generateObject(numPatterns=5)
    self.learn(objectA, numRepetitions=1, randomOrder=True, newObject=True)
    representationA = self._getActiveRepresentation()

    objectB = self.generateObject(numPatterns=5)
    objectB[0] = objectA[0]
    self.learn(objectB, numRepetitions=1, randomOrder=True, newObject=True)
    representationB = self._getActiveRepresentation()

    objectC = self.generateObject(numPatterns=5)
    objectC[0] = objectB[1]
    self.learn(objectC, numRepetitions=1, randomOrder=True, newObject=True)
    representationC = self._getActiveRepresentation()

    self.assertNotEquals(representationA, representationB, representationC)
    # very small overlap
    self.assertLessEqual(len(representationA & representationB), 3)
    self.assertLessEqual(len(representationB & representationC), 3)
    self.assertLessEqual(len(representationA & representationC), 3)


    # check that all patterns except the common one map to the same object
    for pattern in objectA[1:]:
      noisyPattern = self.proximalPatternMachine.addNoise(pattern, 0.05)
      self.infer(feedforwardPattern=noisyPattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationA,
        "The pooled representation for the first object is not stable"
      )

    # check that all patterns except the common one map to the same object
    for pattern in objectB[2:]:
      noisyPattern = self.proximalPatternMachine.addNoise(pattern, 0.05)
      self.infer(feedforwardPattern=noisyPattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationB,
        "The pooled representation for the second object is not stable"
      )

    # check that all patterns except the common one map to the same object
    for pattern in objectC[1:]:
      noisyPattern = self.proximalPatternMachine.addNoise(pattern, 0.05)
      self.infer(feedforwardPattern=noisyPattern)
      self.assertEqual(
        self._getActiveRepresentation(),
        representationC,
        "The pooled representation for the third object is not stable"
      )

    # feed shared pattern between A and B
    pattern = objectA[0]
    noisyPattern = self.proximalPatternMachine.addNoise(pattern, 0.05)
    self.infer(feedforwardPattern=noisyPattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA | representationB,
      "The active representation is incorrect"
    )

    # feed shared pattern between B and C
    pattern = objectB[1]
    noisyPattern = self.proximalPatternMachine.addNoise(pattern, 0.05)
    self.infer(feedforwardPattern=noisyPattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationB | representationC,
      "The active representation is incorrect"
    )

    # feed union of patterns in object A
    pattern = objectA[1] | objectA[2]
    noisyPattern = self.proximalPatternMachine.addNoise(pattern, 0.05)
    self.infer(feedforwardPattern=noisyPattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA,
      "The active representation is incorrect"
    )

    # feed unions of patterns to activate all objects
    pattern = objectA[1] | objectB[1]
    noisyPattern = self.proximalPatternMachine.addNoise(pattern, 0.05)
    self.infer(feedforwardPattern=noisyPattern)
    self.assertEqual(
      self._getActiveRepresentation(),
      representationA | representationB | representationC,
      "The active representation is incorrect"
    )


  def testLearnOneObjectInTwoColumns(self):
    """Learns one object in two different columns."""
    self.init(numCols=2)
    neighborsIndices = [[1], [0]]

    objectA = self.generateObject(numPatterns=5, numCols=2)

    # learn object
    self.learnMultipleColumns(
      objectA,
      numRepetitions=1,
      neighborsIndices=neighborsIndices,
      randomOrder=True,
      newObject=True
    )

    # check inference
    activeRepresentations = self._getActiveRepresentations()

    # TODO: fix this
    # for patternsA in objectA:
    #   self.inferMultipleColumns(
    #     feedforwardPatterns=patternsA,
    #     activeRepresentations=activeRepresentations,
    #     neighborsIndices=neighborsIndices,
    #   )
    #   self.assertEqual(activeRepresentations, self._getActiveRepresentations())
    #   self.assertEqual(activeRepresentations, self._getPredictedActiveCells())


  @unittest.skip("Not working yet")
  def testLearnTwoObjectsInTwoColumnsNoCommonPattern(self):
    """Learns one object in two different columns."""
    self.init(numCols=2)
    neighborsIndices = [[1], [0]]

    objectA = self.generateObject(numPatterns=5, numCols=2)
    objectB = self.generateObject(numPatterns=5, numCols=2)

    # learn object
    self.learnMultipleColumns(
      objectA,
      numRepetitions=1,
      neighborsIndices=neighborsIndices,
      randomOrder=True,
      newObject=True
    )
    activeRepresentationsA = self._getActiveRepresentations()

    # learn object
    self.learnMultipleColumns(
      objectB,
      numRepetitions=1,
      neighborsIndices=neighborsIndices,
      randomOrder=True,
      newObject=True
    )
    activeRepresentationsB = self._getActiveRepresentations()

    # check inference for object A
    # for the first pattern, the distal predictions won't be correct
    firstPattern = True
    for patternsA in objectA:
      self.inferMultipleColumns(
        feedforwardPatterns=patternsA,
        activeRepresentations=activeRepresentationsA,
        neighborsIndices=neighborsIndices,
      )

      if firstPattern:
        firstPattern = False
      else:
        self.assertEqual(
          activeRepresentationsA,
          self._getPredictedActiveCells()
        )
      self.assertEqual(
        activeRepresentationsA,
        self._getActiveRepresentations()
      )

    # check inference for object B
    firstPattern = True
    for patternsB in objectB:
      self.inferMultipleColumns(
        feedforwardPatterns=patternsB,
        activeRepresentations=activeRepresentationsB,
        neighborsIndices=neighborsIndices,
      )

      if firstPattern:
        firstPattern = False
      else:
        self.assertEqual(
          activeRepresentationsB,
          self._getPredictedActiveCells()
        )
      self.assertEqual(
        activeRepresentationsB,
        self._getActiveRepresentations()
      )


  @unittest.skip("Not working yet")
  def testLearnTwoObjectsInTwoColumnsOneCommonPattern(self):
    """Learns one object in two different columns."""
    self.init(numCols=2)
    neighborsIndices = [[1], [0]]

    objectA = self.generateObject(numPatterns=5, numCols=2)
    objectB = self.generateObject(numPatterns=5, numCols=2)

    # second pattern in column 0 is shared
    objectB[1][0] = objectA[1][0]

    # learn object
    self.learnMultipleColumns(
      objectA,
      numRepetitions=1,
      neighborsIndices=neighborsIndices,
      randomOrder=True,
      newObject=True
    )
    activeRepresentationsA = self._getActiveRepresentations()

    # learn object
    self.learnMultipleColumns(
      objectB,
      numRepetitions=1,
      neighborsIndices=neighborsIndices,
      randomOrder=True,
      newObject=True
    )
    activeRepresentationsB = self._getActiveRepresentations()

    # check inference for object A
    # for the first pattern, the distal predictions won't be correct
    # for the second one, the prediction will be unique thanks to the
    # distal predictions from the other column which has no ambiguity
    firstPattern = True
    for patternsA in objectA:
      self.inferMultipleColumns(
        feedforwardPatterns=patternsA,
        activeRepresentations=activeRepresentationsA,
        neighborsIndices=neighborsIndices,
      )

      if firstPattern:
        firstPattern = False
      else:
        self.assertEqual(
          activeRepresentationsA,
          self._getPredictedActiveCells()
        )
      self.assertEqual(
        activeRepresentationsA,
        self._getActiveRepresentations()
      )

    # check inference for object B
    firstPattern = True
    for patternsB in objectB:
      self.inferMultipleColumns(
        feedforwardPatterns=patternsB,
        activeRepresentations=activeRepresentationsB,
        neighborsIndices=neighborsIndices,
      )

      if firstPattern:
        firstPattern = False
      else:
        self.assertEqual(
          activeRepresentationsB,
          self._getPredictedActiveCells()
        )
      self.assertEqual(
        activeRepresentationsB,
        self._getActiveRepresentations()
      )


  def setUp(self):
    """
    Sets up the test.
    """
    # single column case
    self.pooler = None

    # multi column case
    self.poolers = []
    self.proximalPatternMachine = PatternMachine(
      n=self.inputWidth,
      w=self.numOutputActiveBits,
      num=200,
      seed=self.seed
    )

    self.patternId = 0
    np.random.seed(self.seed)


  # Wrappers around ColumnPooler API

  def learn(self,
            feedforwardPatterns,
            lateralPatterns=None,
            numRepetitions=1,
            randomOrder=True,
            newObject=True):
    """
    Parameters:
    ----------------------------
    Learns a single object, with the provided patterns.

    @param   feedforwardPatterns   (list(set))
             List of proximal input patterns

    @param   lateralPatterns       (list(list(set)))
             List of distal input patterns, or None. If no lateral input is
             used. The outer list is expected to have the same length as
             feedforwardPatterns, whereas each inner list's length is the
             number of cortical columns which are distally connected to the
             pooler.

    @param   numRepetitions        (int)
             Number of times the patterns will be fed

    @param   randomOrder           (bool)
             If true, the order of patterns will be shuffled at each
             repetition

    """
    if newObject:
      self.pooler.mmClearHistory()
      self.pooler.reset()

    # set-up
    indices = range(len(feedforwardPatterns))
    if lateralPatterns is None:
      lateralPatterns = [None] * len(feedforwardPatterns)

    for _ in xrange(numRepetitions):
      if randomOrder:
        np.random.shuffle(indices)

      for idx in indices:
        self.pooler.compute(feedforwardPatterns[idx],
                            activeExternalCells=lateralPatterns[idx],
                            learn=True)


  def infer(self,
            feedforwardPattern,
            lateralPatterns=None,
            printMetrics=False):
    """
    Feeds a single pattern to the column pooler (as well as an eventual lateral
    pattern).

    Parameters:
    ----------------------------
    @param feedforwardPattern       (set)
           Input proximal pattern to the pooler

    @param lateralPatterns          (list(set))
           Input dislal patterns to the pooler (one for each neighboring CC's)

    @param printMetrics             (bool)
           If true, will print cell metrics

    """
    self.pooler.compute(feedforwardPattern,
                        activeExternalCells=lateralPatterns,
                        learn=False)

    if printMetrics:
      print self.pooler.mmPrettyPrintMetrics(
        self.pooler.mmGetDefaultMetrics()
      )


  # Helper functions

  def generatePattern(self):
    """
    Returns a random proximal input pattern.
    """
    pattern = self.proximalPatternMachine.get(self.patternId)
    self.patternId += 1
    return pattern


  def generateObject(self, numPatterns, numCols=1):
    """
    Creates a list of patterns, for a given object.

    If numCols > 1 is given, a list of list of patterns will be returned.
    """
    if numCols == 1:
      return [self.generatePattern() for _ in xrange(numPatterns)]

    else:
      patterns = []
      for i in xrange(numPatterns):
        patterns.append([self.generatePattern() for _ in xrange(numCols)])
      return patterns


  def init(self, overrides=None, numCols=1):
    """
    Creates the column pooler with specified parameter overrides.

    Except for the specified overrides and problem-specific parameters, used
    parameters are implementation defaults.
    """
    params = {
      "inputWidth": self.inputWidth,
      "numActivecolumnsPerInhArea": self.numOutputActiveBits,
      "columnDimensions": (self.outputWidth,),
      "seed": self.seed,
      "learnOnOneCell": False
    }
    if overrides is None:
      overrides = {}
    params.update(overrides)

    if numCols == 1:
      self.pooler = MonitoredColumnPooler(**params)
    else:
      # TODO: We need a different seed for each pooler otherwise each one
      # outputs an identical representation. Use random seed for now but ideally
      # we would set different specific seeds for each pooler
      params['seed']=0
      self.poolers = [MonitoredColumnPooler(**params) for _ in xrange(numCols)]


  def _getActiveRepresentation(self):
    """
    Retrieves the current active representation in the pooler.
    """
    if self.pooler is None:
      raise ValueError("No pooler has been instantiated")

    return set(self.pooler.getActiveCells())


  # Multi-column testing

  def learnMultipleColumns(self,
                           feedforwardPatterns,
                           numRepetitions=1,
                           neighborsIndices=None,
                           randomOrder=True,
                           newObject=True):
    """
    Learns a single object, feeding it through the multiple columns.

    Parameters:
    ----------------------------
    Learns a single object, with the provided patterns.

    @param   feedforwardPatterns   (list(list(set)))
             List of proximal input patterns (one for each pooler).


    @param   neighborsIndices      (list(list))
             List of column indices each column received input from.

    @param   numRepetitions        (int)
             Number of times the patterns will be fed

    @param   randomOrder           (bool)
             If true, the order of patterns will be shuffled at each
             repetition

    """
    assert(
      len(feedforwardPatterns) == len(self.poolers),
      "Incorrect number of input proximal patterns"
    )

    if newObject:
      for pooler in self.poolers:
        pooler.mmClearHistory()
        pooler.reset()

    # use different set of pattern indices to allow random orders
    indices = [range(len(feedforwardPatterns[0]))] * len(self.poolers)
    representations = [set()] * len(self.poolers)

    # by default, all columns are neighbors
    if neighborsIndices is None:
      neighborsIndices = [
        range(i) + range(i+1, len(self.poolers))
        for i in xrange(len(self.poolers))
      ]

    for _ in xrange(numRepetitions):
      # independently shuffle pattern orders if necessary
      if randomOrder:
        for idx in indices:
          np.random.shuffle(idx)

      for pattern in indices:

        # get union of relevant lateral representations
        lateralInputs = []
        for col in xrange(len(self.poolers)):
          lateralInputsCol = set()
          for idx in neighborsIndices[col]:
            lateralInputsCol = lateralInputsCol.union(representations[idx])
          lateralInputs.append(lateralInputsCol)

        # Train each column
        for col in xrange(len(self.poolers)):
          self.poolers[col].compute(
            activeColumns=feedforwardPatterns[col][pattern[col]],
            activeExternalCells=lateralInputs[col],
            learn=True
          )

        # update active representations
        representations = self._getActiveRepresentations()


  def inferMultipleColumns(self,
                           feedforwardPatterns,
                           activeRepresentations=None,
                           neighborsIndices=None,
                           printMetrics=False):
    """
    Feeds a single pattern to the column pooler (as well as an eventual lateral
    pattern).

    Parameters:
    ----------------------------
    @param feedforwardPattern       (list(set))
           Input proximal patterns to the pooler (one for each column)

    @param activeRepresentations    (list(set))
           Active representations in the columns at the previous step.

    @param neighborsIndices         (list(list))
           List of column indices each column received input from.

    @param printMetrics             (bool)
           If true, will print cell metrics

    """
    if activeRepresentations is None:
      activeRepresentations = [None] * len(self.poolers)

    # by default, all columns are neighbors
    if neighborsIndices is None:
      neighborsIndices = [
        range(i) + range(i+1, len(self.poolers))
        for i in xrange(len(self.poolers))
      ]

    for i in range(len(self.poolers)):
      lateralInputs = [activeRepresentations[idx] for idx in
                       neighborsIndices[i]]
      self.poolers[i].compute(
        feedforwardPatterns[i],
        activeExternalCells=lateralInputs[i],
        learn=False
      )

    if printMetrics:
      for pooler in self.poolers:
        print pooler.mmPrettyPrintMetrics(
          pooler.mmGetDefaultMetrics()
        )


  def _getActiveRepresentations(self):
    """
    Retrieves the current active representations in the poolers.
    """
    if len(self.poolers) == 0:
      raise ValueError("No pooler has been instantiated")

    return [set(pooler.getActiveCells()) for pooler in self.poolers]


  def _getPredictedActiveCells(self):
    """
    Retrieves the current predicted active cells in the poolers.
    """
    if len(self.poolers) == 0:
      raise ValueError("No pooler has been instantiated")

    return [set(pooler.getPredictedActiveCells()) for pooler in self.poolers]


if __name__ == "__main__":
  unittest.main()
