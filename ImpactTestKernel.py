import math
from abaqus import mdb, session
import part, mesh
from abaqusConstants import *
import regionToolset

class ImpactTestKernel():
    def __init__(self, config):
        self.projectileType = str(config['projectile']['type'])
        self.projectileVelocity = config['projectile']['velocity']
        self.targetObliquity = config['armor']['obliquity']
        self.targetRadius = config['armor']['radius']
        self.targetLayers = config['armor']['layers']
        self.meshElementSize = config['meshElementSize']
        self.assemblyOrder = []

    def run(self):
        self.setModelConstants()
        self.createTargetParts()
        self.createModelAssembly()
        self.createProjectileMesh()
        self.createTargetMesh()
        self.createProjetileSurfaceSets()
        self.createTargetSurfaceSets()
        self.createInteractionProperties()
        self.setInteractions()
        self.applyInitialFields()
        self.applyBoundaryConditions()
        self.adjustOutputs()
        self.createStep()
        self.createJob()

    def setModelConstants(self):
        mdb.models['Model-1'].setValues(absoluteZero=0, stefanBoltzmann=5.67037E-008)

    def createTargetParts(self):
        self.__createTargetSketch()
        i = 1
        for layer in self.targetLayers:
            name = 'Target-L'+str(i).zfill(3)
            part = mdb.models['Model-1'].Part(name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
            part.BaseSolidExtrude(mdb.models['Model-1'].sketches['Target-Sketch'], layer['thickness'])
            part.DatumCsysByDefault(CARTESIAN)
            part.ReferencePoint(point=part.InterestingPoint(edge=part.edges[0], rule=CENTER))
            section = mdb.models['Model-1'].HomogeneousSolidSection(name, str(layer['material']))
            part.SectionAssignment(
                sectionName=name,
                region=regionToolset.Region(
                    cells=part.cells.getSequenceFromMask(
                        mask=('[#1 ]', ),
                    )
                )
            )
            i += 1
            self.assemblyOrder.append((name, layer['thickness']))
            self.__partitionTargetLayer(part, layer['thickness'])

    def createModelAssembly(self):
        assembly = mdb.models['Model-1'].rootAssembly
        assembly.DatumCsysByDefault(CARTESIAN)
        offset = 0.0
        for element in self.assemblyOrder:
            name = element[0]
            thickness = element[1]
            offset -= thickness
            part = mdb.models['Model-1'].parts[name]
            instance = assembly.Instance(name=name, part=part, dependent=ON)
            assembly.translate(instanceList=(name, ), vector=(0.0, 0.0, offset))
        core = mdb.models['Model-1'].parts['Core_'+str(self.projectileType)]
        casing = mdb.models['Model-1'].parts['Casing_'+str(self.projectileType)]
        stdOffset = 0.005 - offset/math.cos(math.pi*self.targetObliquity/180.0)
        xyzOffset = (
            0.0,
            0.0,
            stdOffset
        )
        axisPt = (0.0, 0.0, offset/2.0)
        axisDir = (1.0, 0.0, 0.0)
        for part in (core, casing):
            assembly.Instance(name=part.name, part=part, dependent=ON)
        assembly.translate(
            instanceList=(core.name, casing.name),
            vector=xyzOffset
        )
        assembly.rotate(
            instanceList=(core.name, casing.name),
            axisPoint=axisPt,
            axisDirection=axisDir,
            angle=self.targetObliquity
        )
        xyzOffset = (
            0.0,
            -0.25*self.targetRadius*math.sin(math.pi*self.targetObliquity/180.0),
            0.0
        )
        assembly.translate(
            instanceList=(core.name, casing.name),
            vector=xyzOffset
        )

    def createJob(self):
        pass

    def createStep(self):
        pass

    def adjustOutputs(self):
        pass

    def applyBoundaryConditions(self):
        self.__encastreTargetSides()

    def applyInitialFields(self):
        self.__applyProjectileVelocity()
        self.__applyInitialTemperature()

    def setInteractions(self):
        pass

    def createInteractionProperties(self):
        pass

    #TODO: Find out a way to select inner and outer element faces separately
    def createTargetSurfaceSets(self):
        for element in self.assemblyOrder:
            pass
            #part.Surface(side2Faces=innerElementFaces, name="inner")
            #part.Surface(side1Faces=outerElementFaces, name="outer")

    def createProjetileSurfaceSets(self):
        pass

    def createTargetMesh(self):
        for element in self.assemblyOrder:
            name = element[0]
            part = mdb.models['Model-1'].parts[name]
            regions = part.cells.getSequenceFromMask(mask=('[#3 ]', ), )
            part.setMeshControls(regions=regions, technique=STRUCTURED)
            regions = part.cells.getSequenceFromMask(mask=('[#4 ]', ), )
            part.setMeshControls(regions=regions, algorithm=MEDIAL_AXIS)
            part.seedPart(size=self.meshElementSize, deviationFactor=0.1, minSizeFactor=0.1)
            edges = part.edges.getSequenceFromMask(mask=('[#9300 ]', ), )
            part.seedEdgeByNumber(edges=edges, number=30)
            edges = part.edges.getSequenceFromMask(mask=('[#55 ]', ), )
            part.seedEdgeBySize(edges=edges, size=self.meshElementSize*20.0, deviationFactor=0.1)
            elemType1 = mesh.ElemType(elemCode=C3D8RT, elemLibrary=EXPLICIT,
                                      kinematicSplit=AVERAGE_STRAIN, secondOrderAccuracy=OFF,
                                      hourglassControl=ENHANCED, distortionControl=DEFAULT, elemDeletion=ON)
            part.setElementType(regions=(part.cells, ), elemTypes=(elemType1, ))
            part.generateMesh()


    def createProjectileMesh(self):
        core = mdb.models['Model-1'].parts['Core_'+str(self.projectileType)]
        corec = core.cells.getSequenceFromMask(mask=('[#1 ]', ), )
        core.setMeshControls(regions=corec, algorithm=MEDIAL_AXIS)
        core.seedPart(size=self.meshElementSize, deviationFactor=0.1, minSizeFactor=0.1)
        core.setElementType(
            regions=(corec, ),
            elemTypes=(
                mesh.ElemType(
                    elemCode=C3D8RT,
                    elemLibrary=EXPLICIT,
                    kinematicSplit=AVERAGE_STRAIN,
                    secondOrderAccuracy=OFF,
                    hourglassControl=ENHANCED,
                    distortionControl=DEFAULT,
                    elemDeletion=OFF
                ),
            )
        )
        core.generateMesh()
        casing = mdb.models['Model-1'].parts['Casing_'+str(self.projectileType)]
        casingc = casing.cells.getSequenceFromMask(mask=('[#1 ]', ), )
        casing.setMeshControls(regions=casingc, elemShape=TET, technique=FREE)
        casing.seedPart(size=self.meshElementSize, deviationFactor=0.1, minSizeFactor=0.1)
        casing.setElementType(
            regions=(casingc, ),
            elemTypes=(
                mesh.ElemType(
                    elemCode=C3D10MT,
                    elemLibrary=EXPLICIT,
                    secondOrderAccuracy=OFF,
                    hourglassControl=ENHANCED,
                    distortionControl=DEFAULT,
                    elemDeletion=OFF
                ),
            )
        )
        casing.generateMesh()

    def __createTargetSketch(self):
        radians = math.pi*self.targetObliquity/180.0
        upScale=1.0/math.cos(radians)
        sketch = mdb.models['Model-1'].ConstrainedSketch('Target-Sketch', self.targetRadius*2.0)
        sketch.EllipseByCenterPerimeter(
            center=(0.0, 0.0),
            axisPoint1=(0.0, self.targetRadius*upScale),
            axisPoint2=(self.targetRadius, 0.0)
        )
        innerRadius = self.targetRadius/2.0
        innerSketch = mdb.models['Model-1'].ConstrainedSketch('Inner-Sketch', innerRadius*2.0)
        innerSketch.EllipseByCenterPerimeter(
            center=(0.0, 0.0),
            axisPoint1=(0.0, innerRadius*upScale),
            axisPoint2=(innerRadius, 0.0)
        )

    def __calculateTargetThickness(self):
        thickness = 0.0
        for layer in self.targetLayers:
            thickness += layer['thickness']
        return thickness

    def __partitionTargetLayer(self, part, thickness):
        faces, edges, datums = part.faces, part.edges, part.datums
        transform = part.MakeSketchTransform(
            sketchPlane=faces[1],
            sketchUpEdge=datums[2].axis2,
            sketchPlaneSide=SIDE1,
            origin=(0.0, 0.0, thickness)
        )
        sketch = mdb.models['Model-1'].ConstrainedSketch(
            name='__profile__',
            sheetSize=self.targetRadius/2.0,
            gridSpacing=0.001,
            transform=transform
        )
        geometry, vertices, dimensions, constraints = (
            sketch.geometry,
            sketch.vertices,
            sketch.dimensions,
            sketch.constraints
        )
        sketch.sketchOptions.setValues(decimalPlaces=3)
        sketch.setPrimaryObject(option=SUPERIMPOSE)
        part.projectReferencesOntoSketch(sketch=sketch, filter=COPLANAR_EDGES)
        part = mdb.models['Model-1'].parts[part.name]
        sketch.retrieveSketch(sketch=mdb.models['Model-1'].sketches['Inner-Sketch'])
        faces = part.faces
        pickedFaces = faces.getSequenceFromMask(mask=('[#2 ]', ), )
        edges, datums = part.edges, part.datums
        part.PartitionFaceBySketch(
            sketchUpEdge=datums[2].axis2,
            faces=pickedFaces,
            sketch=sketch
        )
        sketch.unsetPrimaryObject()
        del mdb.models['Model-1'].sketches['__profile__']
        cells = part.cells
        pickedCells = cells.getSequenceFromMask(mask=('[#1 ]', ), )
        edges, datums = part.edges, part.datums
        pickedEdges = (edges[1], )
        part.PartitionCellByExtrudeEdge(
            line=datums[2].axis3,
            cells=pickedCells,
            edges=pickedEdges,
            sense=REVERSE
        )
        part.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=0.0)
        cells = part.cells
        pickedCells = cells.getSequenceFromMask(mask=('[#1 ]', ), )
        datums = part.datums
        part.PartitionCellByDatumPlane(datumPlane=datums[7], cells=pickedCells)

    def __encastreTargetSides(self):
        assembly = mdb.models['Model-1'].rootAssembly
        faces = []
        for layer in self.assemblyOrder:
            name = layer[0]
            faces.append(assembly.instances[name].faces.getSequenceFromMask(
                    mask=(
                        '[#204 ]',
                    ),
                )
            )
        facesSet = faces[0]
        for i in range(1, len(faces)):
            facesSet = facesSet+faces[i]
        region = assembly.Set(faces=facesSet, name='Target-sides')
        mdb.models['Model-1'].EncastreBC(
            name='Fix-sides',
            createStepName='Initial',
            region=region,
            localCsys=None
        )

    def __applyProjectileVelocity(self):
        assembly = mdb.models['Model-1'].rootAssembly
        cells = assembly.instances['Core_'+self.projectileType].cells.getSequenceFromMask(
            mask=(
                '[#1 ]',
            ),
        )
        cells = cells + assembly.instances['Casing_'+self.projectileType].cells.getSequenceFromMask(
            mask=(
                '[#1 ]',
            ),
        )
        region = assembly.Set(
            cells=cells,
            name='Projectile-volume'
        )
        radians = self.targetObliquity*math.pi/180.0
        velocityY = self.projectileVelocity*math.sin(radians)
        velocityZ = -self.projectileVelocity*math.cos(radians)
        mdb.models['Model-1'].Velocity(
            name='Projectile-velocity',
            region=region,
            field='',
            distributionType=MAGNITUDE,
            velocity1=0.0,
            velocity2=velocityY,
            velocity3=velocityZ,
            omega=0.0
        )

    def __applyInitialTemperature(self):
        assembly = mdb.models['Model-1'].rootAssembly
        cells = assembly.instances['Core_'+self.projectileType].cells.getSequenceFromMask(
            mask=(
                '[#1 ]',
            ),
        )
        cells = cells + assembly.instances['Casing_'+self.projectileType].cells.getSequenceFromMask(
            mask=(
                '[#1 ]',
            ),
        )
        for layer in self.assemblyOrder:
            name = layer[0]
            cells = cells + assembly.instances[name].cells.getSequenceFromMask(
                mask=(
                    '[#7 ]',
                ),
            )
        region = assembly.Set(
            cells=cells,
            name='Entire-mass'
        )
        mdb.models['Model-1'].Temperature(
            name='Temperature',
            createStepName='Initial',
            region=region,
            distributionType=UNIFORM,
            crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
            magnitudes=(293.0, )
        )

