from abaqusGui import getAFXApp


# Root function for the plugin
def init():
    # Abaqus 'Plugins' toolset
    toolset = getAFXApp().getAFXMainWindow().getPluginToolset()
    # Attach 'ImpactTest' plugin to the toolset
    toolset.registerKernelMenuButton(
        buttonText='ImpactTest',
        # Plugin's main module
        moduleName="ImpactTestGUI",
        # Module's function to be invoked
        functionName="run()",
        author='Szymon Durak',
        description='Ballistic impact model designer',
        version='0.2',
        helpUrl='https://github.com/superdurszlak/ImpactTest/blob/master/README.md'
    )


init()
