import math
import multiprocessing
import os

from abaqus import mdb, session
import part, mesh
from abaqusConstants import *
import regionToolset



class ImpactTestKernel():
    # Initialize impact test kernel basing on configuration passed
    def __init__(self, config, modelName="Model-1"):
        # Model name - used both as model's name, job's name and input file name
        self.modelName = modelName
        # Create new model database if not default
        if modelName != "Model-1":
            mdb.Model(self.modelName)
            # If model is other than default parts and materials must be imported again
            from ImpactTestStart import importMaterials, importParts
            importMaterials(self.modelName)
            importParts(self.modelName)
            del mdb.models['Model-1']
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
        # Auxilliary list to store layer names, thicknesses and spacings in [m]
        self.assemblyOrder = []

    # Perform all possible steps of model preparation
    def run(self):
        self.adjustDisplacementsAtFailure()
        self.setModelConstants()
        self.createTargetParts()
        self.createModelAssembly()
        self.createProjectileMesh()
        self.createTargetMesh()
        self.createFakeSurfaceSets()
        self.createInteractionProperties()
        self.createInteractions()
        self.createTieConstraints()
        self.applyInitialFields()
        self.applyBoundaryConditions()
        self.createStep()
        self.adjustOutputs()
        self.createJob()
        # self.injectContactToInput()

    # Set absolute zero temperature and Stefan-Boltzmann constant
    def setModelConstants(self):
        mdb.models[self.modelName].setValues(
            # Temperatures will be treated as [K]
            absoluteZero=0,
            stefanBoltzmann=5.67037E-008
        )

    # Create separate part for each target layer
    def createTargetParts(self):
        self.__createTargetSketches()
        i = 1
        for layer in self.targetLayers:
            # Provide uniform target layer naming convention
            name = 'Target-L' + str(i).zfill(3)
            inner_name = name + "I"
            outer_name = name + "O"
            # Create deformable, three dimensional solids from common target sketches
            # Inner part
            part = mdb.models[self.modelName].Part(
                inner_name,
                dimensionality=THREE_D,
                type=DEFORMABLE_BODY)
            part.BaseSolidExtrude(
                mdb.models[self.modelName].sketches['Target-Sketch-Inner'],
                layer['thickness']
            )
            part.DatumCsysByDefault(CARTESIAN)
            part.ReferencePoint(
                point=part.InterestingPoint(
                    edge=part.edges[0],
                    rule=CENTER
                )
            )
            # Assign target layer its material
            section = mdb.models[self.modelName].HomogeneousSolidSection(
                inner_name,
                str(layer['material'])
            )
            part.SectionAssignment(
                sectionName=inner_name,
                region=regionToolset.Region(
                    cells=part.cells.getSequenceFromMask(
                        mask=
                        (
                            '[#1 ]',
                        ),
                    )
                )
            )
            # Outer part
            part = mdb.models[self.modelName].Part(
                outer_name,
                dimensionality=THREE_D,
                type=DEFORMABLE_BODY)
            part.BaseSolidExtrude(
                mdb.models[self.modelName].sketches['Target-Sketch-Outer'],
                layer['thickness']
            )
            part.DatumCsysByDefault(CARTESIAN)
            part.ReferencePoint(
                point=part.InterestingPoint(
                    edge=part.edges[0],
                    rule=CENTER
                )
            )
            # Assign target layer its material
            section = mdb.models[self.modelName].HomogeneousSolidSection(
                outer_name,
                str(layer['material'])
            )
            part.SectionAssignment(
                sectionName=outer_name,
                region=regionToolset.Region(
                    cells=part.cells.getSequenceFromMask(
                        mask=
                        (
                            '[#1 ]',
                        ),
                    )
                )
            )
            i += 1
            # Add layer name and thickness to auxiliary layer list
            self.assemblyOrder.append(
                (
                    name,
                    layer['thickness'],
                    layer['spacing']
                )
            )
            # Cut outer target layer in two
            self.__partitionTargetLayer(part)

    # Create model assembly out of target layers and projectile core and casing
    def createModelAssembly(self):
        assembly = mdb.models[self.modelName].rootAssembly
        assembly.DatumCsysByDefault(CARTESIAN)
        offset = 0.0
        previousSpacing = 0.0
        # Create instances of target layers placed one behind another
        for element in self.assemblyOrder:
            name = element[0]
            inner_name = name + "I"
            outer_name = name + "O"
            thickness = element[1]
            spacing = element[2]
            offset -= thickness + previousSpacing
            verticalOffset = -math.sin(math.pi * self.targetObliquity / 180.0) * offset
            # Outer target part instance
            part = mdb.models[self.modelName].parts[outer_name]
            assembly.Instance(
                name=outer_name,
                part=part,
                dependent=ON
            )
            # Inner target part instance
            part = mdb.models[self.modelName].parts[inner_name]
            assembly.Instance(
                name=inner_name,
                part=part,
                dependent=ON
            )
            assembly.translate(
                instanceList=
                (
                    outer_name,
                    inner_name
                ),
                vector=
                (
                    0.0,
                    verticalOffset,
                    offset
                )
            )
            previousSpacing = spacing
        core = mdb.models[self.modelName].parts['Core_' + str(self.projectileType)]
        casing = mdb.models[self.modelName].parts['Casing_' + str(self.projectileType)]
        offset = self.assemblyOrder[0][1]
        # Projectile offset preventing possible overlapping with target
        stdOffset = 0.0005 + offset / math.cos(math.pi * self.targetObliquity / 180.0)
        xyzOffset = (
            0.0,
            0.0,
            stdOffset
        )
        # Projectile's center of rotation placed in the middle of target's first layer's thickness
        axisPt = (
            0.0,
            0.0,
            -offset / 2.0
        )
        axisDir = (
            1.0,
            0.0,
            0.0
        )
        # Create instances of projectile casing and core
        for part in (core, casing):
            assembly.Instance(
                name=part.name,
                part=part,
                dependent=ON
            )
        # Translate projectile away from the target
        assembly.translate(
            instanceList=
            (
                core.name,
                casing.name
            ),
            vector=xyzOffset
        )
        # Rotate projectile to introduce target's obliquity
        assembly.rotate(
            instanceList=
            (
                core.name,
                casing.name
            ),
            axisPoint=axisPt,
            axisDirection=axisDir,
            angle=self.targetObliquity
        )
        # Translate projectile lower to compromise possible slipping/ricochet
        xyzOffset = (
            0.0,
            -0.1875 * self.targetRadius * math.sin(math.pi * self.targetObliquity / 180.0),
            0.0
        )
        assembly.translate(
            instanceList=
            (
                core.name,
                casing.name
            ),
            vector=xyzOffset
        )

    # Create job for the model
    def createJob(self):
        # Allow use of multiple CPUs/cores
        cpus=multiprocessing.cpu_count()
        job = mdb.Job(
            name=self.modelName,
            model=self.modelName,
            description='',
            type=ANALYSIS,
            atTime=None,
            waitMinutes=0,
            waitHours=0,
            queue=None,
            memory=90,
            memoryUnits=PERCENTAGE,
            getMemoryFromAnalysis=True,
            explicitPrecision=SINGLE,
            nodalOutputPrecision=SINGLE,
            echoPrint=OFF,
            modelPrint=OFF,
            contactPrint=OFF,
            historyPrint=OFF,
            userSubroutine='',
            scratch='',
            resultsFormat=ODB,
            parallelizationMethodExplicit=DOMAIN,
            numDomains=cpus,
            activateLoadBalancing=False,
            multiprocessingMode=DEFAULT,
            numCpus=cpus
        )
        job.writeInput(consistencyChecking=OFF)

    # Create simulation step for impact and penetration phase
    def createStep(self):
        mdb.models[self.modelName].TempDisplacementDynamicsStep(
            name='Impact',
            previous='Initial',
            timePeriod=self.__calculateTargetAbsoluteThickness() * 25.0 / self.projectileVelocity
        )

    # Create proper field/history output requests
    def adjustOutputs(self):
        mdb.models[self.modelName].historyOutputRequests['H-Output-1'].setValues(
            numIntervals=1000
        )
        mdb.models[self.modelName].fieldOutputRequests['F-Output-1'].setValues(
            variables=(
                'S',
                'SVAVG',
                'PE',
                'PEVAVG',
                'PEEQ',
                'PEEQVAVG',
                'LE',
                'U',
                'V',
                'A',
                'RF',
                'CSTRESS',
                'NT',
                'HFL',
                'RFL',
                'EVF',
                'STATUS',
                'SDEG'
            ),
            numIntervals=1000
        )

    # Create appropriate boundary conditions for the model
    def applyBoundaryConditions(self):
        self.__encastreTargetSides()

    # Create initial fields of velocity and temperature
    def applyInitialFields(self):
        self.__applyProjectileVelocity()
        self.__applyInitialTemperature()

    # Create common interaction properties assuming friction coefficient equal 0.05 [-] and thermal conductivity
    # equal 50 [W/(m*K)]
    def createInteractionProperties(self):
        mdb.models[self.modelName].ContactProperty('InteractionProperties')
        mdb.models[self.modelName].interactionProperties['InteractionProperties'].TangentialBehavior(
            formulation=PENALTY,
            directionality=ISOTROPIC,
            slipRateDependency=OFF,
            pressureDependency=OFF,
            temperatureDependency=OFF,
            dependencies=0,
            table=(
                (
                    0.05,
                ),
            ),
            shearStressLimit=None,
            maximumElasticSlip=FRACTION,
            fraction=0.005,
            elasticSlipStiffness=None
        )
        mdb.models[self.modelName].interactionProperties['InteractionProperties'].ThermalConductance(
            definition=TABULAR,
            clearanceDependency=ON,
            pressureDependency=OFF,
            temperatureDependencyC=OFF,
            massFlowRateDependencyC=OFF,
            dependenciesC=0,
            clearanceDepTable=(
                (
                    50.0,
                    0.0
                ),
                (
                    0.0,
                    0.001
                )
            )
        )

    # Mesh each target layer
    def createTargetMesh(self):
        for element in self.assemblyOrder:
            name = element[0]
            inner_part = mdb.models[self.modelName].parts[name + "I"]
            outer_part = mdb.models[self.modelName].parts[name + "O"]

            # Make outer, coarsely meshed region structured
            regions = outer_part.cells.getSequenceFromMask(
                mask=
                (
                    '[#1 ]',
                ),
            )
            outer_part.setMeshControls(
                regions=regions,
                technique=STRUCTURED
            )
            # Make inner, finely meshed region medial-axis swept
            regions = inner_part.cells.getSequenceFromMask(
                mask=
                (
                    '[#1 ]',
                ),
            )
            inner_part.setMeshControls(
                regions=regions,
                algorithm=MEDIAL_AXIS
            )
            # Seed inner part with default element size
            inner_part.seedPart(
                size=self.meshElementSize,
                deviationFactor=0.1,
                minSizeFactor=0.1
            )
            # Seed outer part with large element size
            outer_part.seedPart(
                size=self.targetRadius/16.0,
                deviationFactor=0.1,
                minSizeFactor=0.1
            )
            # Assign all target parts C3D8RT explicit element type with hourglass control and element deletion enabled
            elemType1 = mesh.ElemType(
                elemCode=C3D8RT,
                elemLibrary=EXPLICIT,
                kinematicSplit=AVERAGE_STRAIN,
                secondOrderAccuracy=OFF,
                hourglassControl=ENHANCED,
                distortionControl=DEFAULT,
                elemDeletion=ON,
                maxDegradation=0.99
            )
            inner_part.setElementType(
                regions=(
                    inner_part.cells,
                ),
                elemTypes=(
                    elemType1,
                )
            )
            outer_part.setElementType(
                regions=(
                    outer_part.cells,
                ),
                elemTypes=(
                    elemType1,
                )
            )
            # Mesh part
            inner_part.generateMesh()
            outer_part.generateMesh()

    # Mesh projectile's core and casing
    def createProjectileMesh(self):
        core = mdb.models[self.modelName].parts['Core_' + str(self.projectileType)]
        # Make projectile's core medial-axis swept
        corec = core.cells.getSequenceFromMask(
            mask=
            (
                '[#1 ]',
            ),
        )
        core.setMeshControls(
            regions=corec,
            algorithm=MEDIAL_AXIS
        )
        # Seed core with default mesh element size
        core.seedPart(
            size=self.meshElementSize,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )
        # Assign core C3D8RT explicit element type with hourglass control
        core.setElementType(
            regions=(
                corec,
            ),
            elemTypes=(
                mesh.ElemType(
                    elemCode=C3D8RT,
                    elemLibrary=EXPLICIT,
                    kinematicSplit=AVERAGE_STRAIN,
                    secondOrderAccuracy=OFF,
                    hourglassControl=ENHANCED,
                    distortionControl=DEFAULT,
                    elemDeletion=ON,
                    maxDegradation=0.99
                ),
            )
        )
        # Mesh core
        core.generateMesh()
        casing = mdb.models[self.modelName].parts['Casing_' + str(self.projectileType)]
        # Make projectile's casing freely meshed with tetrahedral elements
        casingc = casing.cells.getSequenceFromMask(
            mask=
            (
                '[#1 ]',
            ),
        )
        casing.setMeshControls(
            regions=casingc,
            elemShape=TET,
            technique=FREE
        )
        # Seed casing with default element size (note that tip's elements will be considerably smaller!)
        casing.seedPart(
            size=self.meshElementSize,
            deviationFactor=0.1,
            minSizeFactor=0.1
        )
        # Assign casing C3D10MT explicit element type (second-order tetrahedral) with hourglass control
        casing.setElementType(
            regions=
            (
                casingc,
            ),
            elemTypes=
            (
                mesh.ElemType(
                    elemCode=C3D4T,
                    elemLibrary=EXPLICIT,
                    secondOrderAccuracy=OFF,
                    elemDeletion=ON,
                    maxDegradation=0.99
                ),
            )
        )
        # Mesh casing
        casing.generateMesh()

    # Create common outer and inner target part sketches for all target layers
    def __createTargetSketches(self):
        # Conversion from [deg] to [rad]
        radians = math.pi * self.targetObliquity / 180.0
        # Stretch ratio reducing risk of projectile entering coarsely meshed area of target
        stretch = 1.0 / math.cos(radians)
        # Create elliptic target sketch
        sketch = mdb.models[self.modelName].ConstrainedSketch('Target-Sketch-Outer', self.targetRadius * 2.0)
        # Outer bound
        sketch.EllipseByCenterPerimeter(
            center=
            (
                0.0,
                0.0
            ),
            axisPoint1=
            (
                0.0,
                self.targetRadius * stretch
            ),
            axisPoint2=
            (
                self.targetRadius,
                0.0
            )
        )
        # Inner bound
        innerRadius = self.targetRadius / 2.0
        sketch.EllipseByCenterPerimeter(
            center=
            (
                0.0,
                0.0
            ),
            axisPoint1=
            (
                0.0,
                innerRadius * stretch
            ),
            axisPoint2=
            (
                innerRadius,
                0.0
            )
        )
        # Create elliptic target partition sketch
        innerSketch = mdb.models[self.modelName].ConstrainedSketch(
            'Target-Sketch-Inner',
            innerRadius * 2.0
        )
        innerSketch.EllipseByCenterPerimeter(
            center=
            (
                0.0,
                0.0
            ),
            axisPoint1=
            (
                0.0,
                innerRadius * stretch
            ),
            axisPoint2=
            (
                innerRadius,
                0.0
            )
        )

    # Combine thicknesses of all target layers
    def __calculateTargetAbsoluteThickness(self):
        thickness = 0.0
        for layer in self.targetLayers:
            thickness += layer['thickness'] + layer['spacing']
        return thickness

    # Partition each target layer
    def __partitionTargetLayer(self, part):
        # Partition target's outer cell to allow hex swept meshing
        part.DatumPlaneByPrincipalPlane(
            principalPlane=YZPLANE,
            offset=0.0
        )
        cells = part.cells
        pickedCells = cells.getSequenceFromMask(
            mask=
            (
                '[#1 ]',
            ),
        )
        datums = part.datums
        part.PartitionCellByDatumPlane(
            datumPlane=datums[5],
            cells=pickedCells
        )

    # Create 'encastre' boundary condition on sides of each target layer
    def __encastreTargetSides(self):
        assembly = mdb.models[self.modelName].rootAssembly
        # Create list of selections
        faces = []
        for layer in self.assemblyOrder:
            name = layer[0] + "O"
            faces.append(assembly.instances[name].faces.getSequenceFromMask(
                mask=
                (
                    '[#48 ]',
                ),
            )
            )
        # Combine selections and create set
        facesSet = faces[0]
        for i in range(1, len(faces)):
            facesSet = facesSet + faces[i]
        region = assembly.Set(
            faces=facesSet,
            name='Target-sides'
        )
        # Create boundary condition
        mdb.models[self.modelName].EncastreBC(
            name='Fix-sides',
            createStepName='Initial',
            region=region,
            localCsys=None
        )

    # Create uniform velocity field on projectile
    def __applyProjectileVelocity(self):
        assembly = mdb.models[self.modelName].rootAssembly
        # Create selection out of casing's and core's cells
        cells = assembly.instances['Core_' + self.projectileType].cells.getSequenceFromMask(
            mask=
            (
                '[#1 ]',
            ),
        )
        cells = cells + assembly.instances['Casing_' + self.projectileType].cells.getSequenceFromMask(
            mask=
            (
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
        mdb.models[self.modelName].Velocity(
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
        assembly = mdb.models[self.modelName].rootAssembly
        # Create selection out of target's and projectile's cells
        cells = assembly.instances['Core_' + self.projectileType].cells.getSequenceFromMask(
            mask=
            (
                '[#1 ]',
            ),
        )
        cells = cells + assembly.instances['Casing_' + self.projectileType].cells.getSequenceFromMask(
            mask=
            (
                '[#1 ]',
            ),
        )
        for layer in self.assemblyOrder:
            name = layer[0]
            cells = cells + assembly.instances[name + "I"].cells.getSequenceFromMask(
                mask=
                (
                    '[#1 ]',
                ),
            )
            cells = cells + assembly.instances[name + "O"].cells.getSequenceFromMask(
                mask=
                (
                    '[#3 ]',
                ),
            )
        # Create set
        region = assembly.Set(
            cells=cells,
            name='Entire-mass'
        )
        # Create temperature field
        mdb.models[self.modelName].Temperature(
            name='Temperature',
            createStepName='Initial',
            region=region,
            distributionType=UNIFORM,
            crossSectionDistribution=CONSTANT_THROUGH_THICKNESS,
            # 293.15 [K] equals to 20 [*C]
            magnitudes=
            (
                293.15,
            )
        )

    # Write job input file, inject surface sets and set interactions between them - it's a workaround that will
    # hopefully solve the problem with setting interior/exterior surface sets in Abaqus
    def injectContactToInput(self):
        job = mdb.models[self.modelName].jobs[self.modelName]
        job.writeInput(
            consistencyChecking=OFF
        )
        filename = self.__getInputFilename()
        lines = self.__obtainLines(filename)
        lines = self.__insertInteractions(lines)
        lines = self.__insertSurfaceSet(lines)
        self.__overrideInput(lines, filename)

    # Load original input file and read its lines
    def __obtainLines(self, filename):
        with open(filename) as file:
            lines = [line.strip('\n') for line in file.readlines()]
            file.close()
        return lines

    # Insert surface set definition to input file lines
    def __insertSurfaceSet(self, lines):
        newlines = []
        newlines.append('**')
        newlines.append('** ELEMENT SURFACE SETS')
        newlines.append('**')
        for inst in mdb.models[self.modelName].rootAssembly.instances.values():
            newlines.append('** %s' % inst.name)
            newlines.append('** %s' % inst.name)
        index = self.__getEndAssemblyIdx(lines)
        lines[index:index] = newlines
        # TODO: Implement surface set definition insertion
        return lines

    # Insert interaction definition to input file lines
    def __insertInteractions(self, lines):
        newlines = []
        newlines.append('**')
        newlines.append('** INTERACTIONS')
        newlines.append('**')
        index = self.__getLastMaterialConstantIdx(lines)
        lines[index:index] = newlines
        # TODO: Implement interaction definition insertion
        return lines

    # Override input file with modified lines
    def __overrideInput(self, lines, filename):
        with open(filename, 'w') as file:
            for line in lines:
                file.write("%s\n" % line)
            file.close()
        return

    # Obtain input filename
    def __getInputFilename(self):
        fname = __file__
        for i in range(0, 7):
            fname = os.path.dirname(fname)
        fname = fname + "/Commands/"+self.modelName+".inp"
        return fname

    # Obtain line index under which our properties should be inserted
    def __getLastMaterialConstantIdx(self, lines):
        for line in reversed(lines):
            if line.startswith('Entire-mass'):
                return lines.index(line) + 1

    # Find index of the line after '*End Assembly [...]' line
    def __getEndAssemblyIdx(self, lines):
        for line in reversed(lines):
            if line.startswith('*End Assembly'):
                return lines.index(line) - 1

    # Adjust materials' displacement criterion for J-C damage evolution to element's size
    def adjustDisplacementsAtFailure(self):
        for material in mdb.models[self.modelName].materials.values():
            if material.johnsonCookDamageInitiation is not None:
                if material.johnsonCookDamageInitiation.damageEvolution is not None:
                    strainAtFailure = material.johnsonCookDamageInitiation.damageEvolution.table[0][0]
                    displacementAtFailure = strainAtFailure * self.meshElementSize
                    material.johnsonCookDamageInitiation.damageEvolution.setValues(
                        table=
                        (
                            (
                                displacementAtFailure,
                            ),
                        )
                    )

    # Create fake surface sets - they must be reselected by the user
    def createFakeSurfaceSets(self):
        # FIXME: Make Surface objects actually re-definable as mesh surfaces
        assembly = mdb.models[self.modelName].rootAssembly
        faces = assembly.instances['Target-L001I'].faces
        faces = faces.getSequenceFromMask(
            mask=
            (
                '[#2 ]',
            ),
        )
        faceSet = assembly.Set(
            faces=faces,
            name='Fake-contact-set'
        )
        assembly.SurfaceFromElsets(
            name="Interior-Brown",
            elementSetSeq=
            (
                (
                    faceSet,
                    S1
                ),
                (
                    faceSet,
                    S2
                )
            )
        )
        assembly.SurfaceFromElsets(
            name="Interior-Purple",
            elementSetSeq=
            (
                (
                    faceSet,
                    S1
                ),
                (
                    faceSet,
                    S2
                )
            )
        )
        assembly.SurfaceFromElsets(
            name="Exterior",
            elementSetSeq=
            (
                (
                    faceSet,
                    S1
                ),
                (
                    faceSet,
                    S2
                )
            )
        )

    # Create interaction to handle contact between all mesh element faces
    def createInteractions(self):
        mdb.models[self.modelName].ContactExp(
            name='Contact',
            createStepName='Initial'
        )
        ext = mdb.models[self.modelName].rootAssembly.surfaces['Exterior']
        inb = mdb.models[self.modelName].rootAssembly.surfaces['Interior-Brown']
        inp = mdb.models[self.modelName].rootAssembly.surfaces['Interior-Purple']
        mdb.models[self.modelName].interactions['Contact'].includedPairs.setValuesInStep(
            stepName='Initial',
            useAllstar=OFF,
            addPairs=(
                (
                    ext,
                    SELF
                ),
                (
                    ext,
                    inb
                ),
                (
                    inb,
                    ext
                ),
                (
                    inp,
                    SELF
                ),
                (
                    inb,
                    inp
                ),
                (
                    inp,
                    inb
                ),
                (
                    inp,
                    SELF
                )
            )
        )
        mdb.models[self.modelName].interactions['Contact'].contactPropertyAssignments.appendInStep(
            stepName='Initial',
            assignments=(
                (
                    GLOBAL,
                    SELF,
                    'InteractionProperties'
                ),
            )
        )

    def createTieConstraints(self):
        for layer in self.assemblyOrder:
            name = layer[0]
            inner_name = name + "I"
            outer_name = name + "O"
            assembly = mdb.models[self.modelName].rootAssembly
            inner_faces = assembly.instances[inner_name].faces.getSequenceFromMask(
                mask=(
                  '[#1 ]',
                ),
            )
            assembly.Surface(
                side1Faces=inner_faces,
                name=inner_name + "_TIE"
            )
            inner_region = assembly.surfaces[inner_name+"_TIE"]
            outer_faces = assembly.instances[outer_name].faces.getSequenceFromMask(
                mask=(
                  '[#a0 ]',
                ),
            )
            assembly.Surface(
                side1Faces=outer_faces,
                name=outer_name + "_TIE"
            )
            outer_region = assembly.surfaces[outer_name+"_TIE"]
            mdb.models[self.modelName].Tie(
                name=name + "_TIE",
                master=outer_region,
                slave=inner_region,
                positionToleranceMethod=COMPUTED,
                adjust=ON,
                constraintEnforcement=SURFACE_TO_SURFACE
            )
