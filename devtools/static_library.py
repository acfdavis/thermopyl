from setuptools import Extension
import shutil
import os

class StaticLibrary(Extension):
    def __init__(self, *args, export_include=None, **kwargs):
        self.export_include = export_include or []
        super().__init__(*args, **kwargs)

def build_static_extension(build_ext_instance, ext):
    from distutils import log
    from distutils.dep_util import newer_group
    sources = ext.sources
    if sources is None or not isinstance(sources, (list, tuple)):
        raise RuntimeError(
              ("in 'ext_modules' option (extension '%s'), " +
               "'sources' must be present and must be " +
               "a list of source filenames") % ext.name)
    sources = list(sources)
    ext_path = build_ext_instance.get_ext_fullpath(ext.name)
    depends = sources + ext.depends
    if not (build_ext_instance.force or newer_group(depends, ext_path, 'newer')):
        log.debug("skipping '%s' extension (up-to-date)", ext.name)
        return
    else:
        log.info("building '%s' extension", ext.name)
    extra_args = ext.extra_compile_args or []
    macros = ext.define_macros[:]
    for undef in ext.undef_macros:
        macros.append((undef,))
    objects = build_ext_instance.compiler.compile(sources,
                                     output_dir=build_ext_instance.build_temp,
                                     macros=macros,
                                     include_dirs=ext.include_dirs,
                                     debug=build_ext_instance.debug,
                                     extra_postargs=extra_args,
                                     depends=ext.depends)
    build_ext_instance._built_objects = objects[:]
    if ext.extra_objects:
        objects.extend(ext.extra_objects)
    extra_args = ext.extra_link_args or []
    language = ext.language or build_ext_instance.compiler.detect_language(sources)
    libname = os.path.splitext(os.path.basename(ext_path))[0]
    output_dir = os.path.dirname(ext_path)
    if (getattr(build_ext_instance.compiler, 'static_lib_format', 'lib%s.a').startswith('lib') and
        libname.startswith('lib')):
        libname = libname[3:]
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    build_ext_instance.compiler.create_static_lib(objects,
        output_libname=libname,
        output_dir=output_dir,
        target_lang=language)
    for item in ext.export_include:
        shutil.copy(item, output_dir)
