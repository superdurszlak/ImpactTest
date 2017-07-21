# ImpactTest
ImpactTest is Abaqus 6.14 plugin intended to support designing numerical models for armor penetration. It is being created in order to simplify and speed up the process of preparing multiple models for slightly different test cases, f.e. penetrator striking the armor plate at different angles or with different velocities.

### Formalities
The plugin is in fact a side-project to my Engineer's Thesis "Formulation of numerical model for multilayer armor penetration process". Thus you can feel free to use or modify the plugin on your own responsibility, although due to procedural reasons I might have no choice but reject potential contributions to the core project.

### Setup
In order to use the plugin, simply paste the project's root directory to /.../abaqus_plugins/ and run the ./setup.py script, which should compile all necessary scripts for you. Instead, you can also compile them on your own using your favourite tool.

### Bullet parts and material libraries
The plugin does not, and never will provide out-of-the-box material libraries nor penetrator parts. Instead, you can paste your custom material libraries to /.../abaqus_plugins/ImpactTest/Materials folder to allow plugin to import them.

You should be able to import custom penetrators in similiar manner in the future, once penetrator generation scripts will have been implemented.
