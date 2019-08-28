# The master toctree document.
master_doc = 'index'

# The suffix of source filenames.
source_suffix = '.rst'

# General information about the project.
project = u'osh-operator'
copyright = u'2005-2019 Mirantis, Inc.'

latex_documents = [
    (
        'index',
        '%s.tex' % project,
        u'%s Documentation' % project,
        u'Mirantis',
        'manual'
    ),
]