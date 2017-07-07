from abaqusGui import getAFXApp

def init():
    toolset = getAFXApp().getAFXMainWindow().getPluginToolset()
    toolset.registerKernelMenuButton(buttonText='Armor Impact',
                                     moduleName="ImpactTestStart",
                                     functionName="run()",
                                     author='Szymon Durak',
                                     description='Armor impact plugin')


init()
