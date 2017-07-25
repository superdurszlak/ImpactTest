from abaqusGui import getAFXApp

#Root function for the plugin
def init():
    #Abaqus 'Plugins' toolset
    toolset = getAFXApp().getAFXMainWindow().getPluginToolset()
    #Attach 'ImpactTest' plugin to the toolset
    toolset.registerKernelMenuButton(
        buttonText='Armor Impact',
        #Plugin's main module
        moduleName="ImpactTestStart",
        #Module's function to be invoked
        functionName="run()",
        author='Szymon Durak',
        description='Armor impact plugin'
    )


init()
