import math
from abaqus import mdb, session
import part, mesh
from abaqusConstants import *
import regionToolset


class ImpactTestKernel():
    # Initialize impact test kernel basing on configuration passed
    def __init__(self, config):
        # Type of projectile - describing subdirectory name
        self.projectileType = str(config['projectile']['type'])
        # Projectile's velocity in [m/s]
        self.projectileVelocity = config['projectile']['velocity']
        # Target obliquity in [deg] - 0 means normal to projectile's direction
        self.targetObliquity = config['armor']['obliquity']
        # Target radius in [m]
        self.targetRadius = config['armor']['radius']
        # List of target layers - describing layers thickness in [m] and material
        self.targetLayers = config['armor']['layers']
        # Average mesh element size in [m] used to seed parts
        self.meshElementSize = config['meshElementSize']
        # Auxilliary list to store layer names and thicknesses in [m]
        self.assemblyOrder = []

    # Perform all possible steps of model preparation
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

    # Set absolute zero temperature and Stafan-Boltzmann constant
    def setModelConstants(self):
        mdb.models['Model-1'].setValues(
            # Temperatures will be treated as [K]
            absoluteZero=0,
            stefanBoltzmann=5.67037E-008
        )

    # Create separate part for each target layer
    def createTargetParts(self):
        self.__createTargetSketch()
        i = 1
        for layer in self.targetLayers:
            # Provide uniform target layer naming convention
            name = 'Target-L' + str(i).zfill(3)
            # Create deformable, three dimensional solid from common target sketch
            part = mdb.models['Model-1'].Part(name, dimensionality=THREE_D, type=DEFORMABLE_BODY)
            part.BaseSolidExtrude(mdb.models['Model-1'].sketches['Target-Sketch'], layer['thickness'])
            part.DatumCsysByDefault(CARTESIAN)
            part.ReferencePoint(point=part.InterestingPoint(edge=part.edges[0], rule=CENTER))
            # Assign target layer its material
            section = mdb.models['Model-1'].HomogeneousSolidSection(name, str(layer['material']))
            part.SectionAssignment(
                sectionName=name,
                region=regionToolset.Region(
                    cells=part.cells.getSequenceFromMask(
                        mask=('[#1 ]',),
                    )
                )
            )
            i += 1
            # Add layer name and thickness to auxiliary layer list
            self.assemblyOrder.append((name, layer['thickness']))
            self.__partitionTargetLayer(part, layer['thickness'])

    # Create model assembly out of target layers and projectile core and casing
    def createModelAssembly(self):
        assembly = mdb.models['Model-1'].rootAssembly
        assembly.DatumCsysByDefault(CARTESIAN)
        offset = 0.0
        # Create instances of target layers placed one behind another
        for element in self.assemblyOrder:
            name = element[0]
            thickness = element[1]
            offset -= thickness
            part = mdb.models['Model-1'].parts[name]
            instance = assembly.Instance(name=name, part=part, dependent=ON)
            assembly.translate(instanceList=(name,), vector=(0.0, 0.0, offset))
        core = mdb.models['Model-1'].parts['Core_' + str(self.projectileType)]
        casing = mdb.models['Model-1'].parts['Casing_' + str(self.projectileType)]
        # Projectile offset preventing possible overlapping with target
        stdOffset = 0.005 - offset / math.cos(math.pi * self.targetObliquity / 180.0)
        xyzOffset = (
            0.0,
            0.0,
            stdOffset
        )
        # Projectile's center of rotation placed in the middle of target's thickness
        axisPt = (0.0, 0.0, offset / 2.0)
        axisDir = (1.0, 0.0, 0.0)
        # Create instances of projectile casing and core
        for part in (core, casing):
            assembly.Instance(name=part.name, part=part, dependent=ON)
        # Translate projectile away from the target
        assembly.translate(
            instanceList=(core.name, casing.name),
            vector=xyzOffset
        )
        # Rotate projectile to introduce target's obliquity
        assembly.rotate(
            instanceList=(core.name, casing.name),
            axisPoint=axisPt,
            axisDirection=axisDir,
            angle=self.targetObliquity
        )
        # Translate projectile lower to compensate possible slipping/ricochet
        xyzOffset = (
            0.0,
            -0.25 * self.targetRadius * math.sin(math.pi * self.targetObliquity / 180.0),
            0.0
        )
        assembly.translate(
            instanceList=(core.name, casing.name),
            vector=xyzOffset
        )

    # TODO: Create job for the model
    def createJob(self):
        pass

    # TODO: Create simulation step for impact and penetration phase
    def createStep(self):
        pass

    # TODO: Create proper field/history output requests
    def adjustOutputs(self):
        pass

    # Create appropriate boundary conditions for the model
    def applyBoundaryConditions(self):
        self.__encastreTargetSides()

    # Create initial fields of velocity and temperature
    def applyInitialFields(self):
        self.__applyProjectileVelocity()
        self.__applyInitialTemperature()

    # TODO: Set proper interactions between target layers and projectile's core and casing
    def setInteractions(self):
        pass

    # TODO: Create proper interaction properties
    def createInteractionProperties(self):
        pass

    # TODO: Select inner and outer element faces separately for target layers
    def createTargetSurfaceSets(self):
        pass
        # part.Surface(side2Faces=innerElementFaces, name="inner")
        # part.Surface(side1Faces=outerElementFaces, name="outer")

    # TODO: Select inner and outer element faces separately for projectile's core and casing
    def createProjetileSurfaceSets(self):
        pass

    # Mesh each target layer
    def createTargetMesh(self):
        for element in self.assemblyOrder:
            name = element[0]
            part = mdb.models['Model-1'].parts[name]
            # Make outer, coarsely meshed region structured
            regions = part.cells.getSequenceFromMask(mask=('[#3 ]',), )
            part.setMeshControls(regions=regions, technique=STRUCTURED)
            # Make inner, finely meshed region medial-axis swept
            regions = part.cells.getSequenceFromMask(mask=('[#4 ]',), )
            part.setMeshControls(regions=regions, algorithm=MEDIAL_AXIS)
            # Seed part with default element size
            part.seedPart(size=self.meshElementSize, deviationFactor=0.1, minSizeFactor=0.1)
            # Let outer edge consist of low number of nodes
            edges = part.edges.getSequenceFromMask(mask=('[#9300 ]',), )
            part.seedEdgeByNumber(edges=edges, number=30)
            # Let outer target region be less densely meshed
            edges = part.edges.getSequenceFromMask(mask=('[#55 ]',), )
            part.seedEdgeBySize(edges=edges, size=self.meshElementSize * 20.0, deviationFactor=0.1)
            # Assign all target cells C3D8RT explicit element type with hourglass control and element deletion enabled
            elemType1 = mesh.ElemType(elemCode=C3D8RT, elemLibrary=EXPLICIT,
                                      kinematicSplit=AVERAGE_STRAIN, secondOrderAccuracy=OFF,
                                      hourglassControl=ENHANCED, distortionControl=DEFAULT, elemDeletion=ON)
            part.setElementType(regions=(part.cells,), elemTypes=(elemType1,))
            # Mesh part
            part.generateMesh()

    # Mesh projectile's core and casing
    def createProjectileMesh(self):
        core = mdb.models['Model-1'].parts['Core_' + str(self.projectileType)]
        # Make projectile's core medial-axis swept
        corec = core.cells.getSequenceFromMask(mask=('[#1 ]',), )
        core.setMeshControls(regions=corec, algorithm=MEDIAL_AXIS)
        # Seed core with default mesh element size
        core.seedPart(size=self.meshElementSize, deviationFactor=0.1, minSizeFactor=0.1)
        # Assign core C3D8RT explicit element type with hourglass control
        core.setElementType(
            regions=(corec,),
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
        # Mesh core
        core.generateMesh()
        casing = mdb.models['Model-1'].parts['Casing_' + str(self.projectileType)]
        # Make projectile's casing freely meshed with tetrahedral elements
        casingc = casing.cells.getSequenceFromMask(mask=('[#1 ]',), )
        casing.setMeshControls(regions=casingc, elemShape=TET, technique=FREE)
        # Seed casing with default element size (note that tip's elements will be considerably smaller!)
        casing.seedPart(size=self.meshElementSize, deviationFactor=0.1, minSizeFactor=0.1)
        # Assign casing C3D10MT explicit element type (second-order tetrahedral) with hourglass control
        casing.setElementType(
            regions=(casingc,),
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
        # Mesh casing
        casing.generateMesh()

    # Create common target and target partition sketches for all target layers
    def __createTargetSketch(self):
        # Conversion from [deg] to [rad]
        radians = math.pi * self.targetObliquity / 180.0
        # Stretch ratio reducing risk of projectile entering coarsely meshed area of target
        stretch = 1.0 / math.cos(radians)
        # Create elliptic target sketch
        sketch = mdb.models['Model-1'].ConstrainedSketch('Target-Sketch', self.targetRadius * 2.0)
        sketch.EllipseByCenterPerimeter(
            center=(0.0, 0.0),
            axisPoint1=(0.0, self.targetRadius * stretch),
            axisPoint2=(self.targetRadius, 0.0)
        )
        # Create elliptic target partition sketch
        innerRadius = self.targetRadius / 2.0
        innerSketch = mdb.models['Model-1'].ConstrainedSketch('Inner-Sketch', innerRadius * 2.0)
        innerSketch.EllipseByCenterPerimeter(
            center=(0.0, 0.0),
            axisPoint1=(0.0, innerRadius * stretch),
            axisPoint2=(innerRadius, 0.0)
        )

    # Combine thicknesses of all target layers
    def __calculateTargetThickness(self):
        thickness = 0.0
        for layer in self.targetLayers:
            thickness += layer['thickness']
        return thickness

    # Partition each target layer
    def __partitionTargetLayer(self, part, thickness):
        faces, edges, datums = part.faces, part.edges, part.datums
        # Create sketch transform
        transform = part.MakeSketchTransform(
            sketchPlane=faces[1],
            sketchUpEdge=datums[2].axis2,
            sketchPlaneSide=SIDE1,
            origin=(0.0, 0.0, thickness)
        )
        # Map common sketch on target's face
        sketch = mdb.models['Model-1'].ConstrainedSketch(
            name='__profile__',
            sheetSize=self.targetRadius / 2.0,
            gridSpacing=0.001,
            transform=transform
        )
        sketch.sketchOptions.setValues(decimalPlaces=3)
        sketch.setPrimaryObject(option=SUPERIMPOSE)
        part.projectReferencesOntoSketch(sketch=sketch, filter=COPLANAR_EDGES)
        part = mdb.models['Model-1'].parts[part.name]
        sketch.retrieveSketch(sketch=mdb.models['Model-1'].sketches['Inner-Sketch'])
        faces = part.faces
        pickedFaces = faces.getSequenceFromMask(mask=('[#2 ]',), )
        edges, datums = part.edges, part.datums
        part.PartitionFaceBySketch(
            sketchUpEdge=datums[2].axis2,
            faces=pickedFaces,
            sketch=sketch
        )
        sketch.unsetPrimaryObject()
        del mdb.models['Model-1'].sketches['__profile__']
        # Select target's cell to partition
        cells = part.cells
        pickedCells = cells.getSequenceFromMask(mask=('[#1 ]',), )
        edges, datums = part.edges, part.datums
        pickedEdges = (edges[1],)
        # Partition target to create inner cell
        part.PartitionCellByExtrudeEdge(
            line=datums[2].axis3,
            cells=pickedCells,
            edges=pickedEdges,
            sense=REVERSE
        )
        # Partition target's outer cell to allow hex swept meshing
        part.DatumPlaneByPrincipalPlane(principalPlane=YZPLANE, offset=0.0)
        cells = part.cells
        pickedCells = cells.getSequenceFromMask(mask=('[#1 ]',), )
        datums = part.datums
        part.PartitionCellByDatumPlane(datumPlane=datums[7], cells=pickedCells)

    # Create 'encastre' boundary condition on sides of each target layer
    def __encastreTargetSides(self):
        assembly = mdb.models['Model-1'].rootAssembly
        # Create list of selections
        faces = []
        for layer in self.assemblyOrder:
            name = layer[0]
            faces.append(assembly.instances[name].faces.getSequenceFromMask(
                mask=(
                    '[#204 ]',
                ),
            )
            )
        # Combine selections and create set
        facesSet = faces[0]
        for i in range(1, len(faces)):
            facesSet = facesSet + faces[i]
        region = assembly.Set(faces=facesSet, name='Target-sides')
        # Create boundary condition
        mdb.models['Model-1'].EncastreBC(
            name='Fix-sides',
            createStepName='Initial',
            region=region,
            localCsys=None
        )

    # Create uniform velocity field on projectile
    def __applyProjectileVelocity(self):
        assembly = mdb.models['Model-1'].rootAssembly
        # Create selection out of casing's and core's cells
        cells = assembly.instances['Core_' + self.projectileType].cells.getSequenceFromMask(
            mask=(
                '[#1 ]',
            ),
        )
        cells = cells + assembly.instances['Casing_' + self.projectileType].cells.getSequenceFromMask(
            mask=(
                '[#1 ]',
            ),
        )
        # Create set
        region = assembly.Set(
            cells=cells,
            name='Projectile-volume'
        )
        # Convert [deg] to [rad]
        radians = self.targetObliquity * math.pi / 180.0
        # Compute velocity vector components
        velocityY = self.projectileVelocity * math.sin(radians)
        velocityZ = -self.projectileVelocity * math.cos(radians)
        # Create velocity field
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

    # Create uniform temperature field on both target and projectile
    def __applyInitialTemperature(self):
        assembly = mdb.models['Model-1'].rootAssembly
        # Create selection out of target's and projectile's cells
        cells = assembly.instances['Core_' + self.projectileType].cells.getSequenceFromMask(
            mask=(
                '[#1 ]',
            ),
        )
        cells = cells + assembly.instances['Casing_' + self.projectileType].cells.getSequenceFromMask(
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
        # Create set
        region = assembly.Set(
            cells=cells,
            name='Entire-mass'
        )
        # Create temperature field
        mdb.models['Model-1'].Temperature(
            name='Temperature',
            createStepName='Initial',
            region=region,
            distributionType=UNIFORM,
            crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
            # 293.15 [K] equals to 20 [*C]
            magnitudes=(293.15,)
        )
