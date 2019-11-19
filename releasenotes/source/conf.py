import time

# The master toctree document.
master_doc = 'index'

# The suffix of source filenames.
source_suffix = '.rst'

# General information about the project.
project = u'openstack-controller Release Notes'
copyright = u'2005-{} Mirantis, Inc.'.format(time.strftime("%Y"))

latex_documents = [
    (
        'index',
        '%s.tex' % project,
        u'%s Release Notes Documentation' % project,
        u'Mirantis',
        'manual'
    ),
]
