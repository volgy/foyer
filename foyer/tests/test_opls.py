import glob
import os

from mbuild.tests.base_test import BaseTest
import parmed as pmd
from pkg_resources import resource_filename
import pytest

from foyer.forcefield import apply_forcefield
from foyer.atomtyper import find_atomtypes


class TestOPLS(BaseTest):

    resource_dir = resource_filename('foyer', '../opls_validation')
    top_files = set(glob.glob(os.path.join(resource_dir, '*.top')))

    # Please update this file if you implement atom typing for a test case.
    implemented_tests_path = os.path.join(os.path.dirname(__file__),
                                          'implemented_opls_tests.txt')
    correctly_implemented = [line.split() for line in open(implemented_tests_path)]
    correctly_implemented_mol_names = {x[0] for x in correctly_implemented}
    correctly_implemented_top_files = {x[1] for x in correctly_implemented}

    def find_topfile_by_mol_name(self, mol_name):
        for top_file in self.top_files:
            with open(top_file) as fh:
                if mol_name in fh.read():
                    return top_file

    def find_correctly_implemented(self):
        with open(self.implemented_tests_path, 'a') as fh:
            for top in self.top_files:
                try:
                    mol_name = self.test_atomtyping(top)
                except:
                    continue
                else:
                    basename = os.path.basename(top)
                    if basename not in self.correctly_implemented_top_files:
                        fh.write('{} {}\n'.format(mol_name, basename))

    @pytest.mark.parametrize('top_path', correctly_implemented_top_files)
    def test_atomtyping(self, top_path, only_run=None):
        top_path = os.path.join(self.resource_dir, top_path)

        base_path, top_filename = os.path.split(top_path)
        gro_file = '{}-gas.gro'.format(top_filename[:-4])
        gro_path = os.path.join(base_path, gro_file)

        structure = pmd.gromacs.GromacsTopologyFile(top_path, xyz=gro_path)
        structure.title = structure.title.replace(' GAS', '')
        known_opls_types = [atom.type for atom in structure.atoms]

        print("Typing {} ({})...".format(structure.title, top_filename))
        find_atomtypes(structure.atoms, forcefield='OPLS-AA', debug=False)

        generated_opls_types = list()
        for i, atom in enumerate(structure.atoms):
            message = ('Found multiple or no OPLS types for atom {} in {} ({}): {}\n'
                       'Should be atomtype: {}'.format(
                i, structure.title, top_filename, atom.type, known_opls_types[i]))
            assert atom.type, message

            generated_opls_types.append(atom.type)
        both = zip(generated_opls_types, known_opls_types)

        n_types = range(len(generated_opls_types))
        message = "Found inconsistent OPLS types in {} ({}): {}".format(
            structure.title, top_filename,
            list(zip(n_types, generated_opls_types, known_opls_types)))

        assert all([a == b for a, b in both]), message
        return structure.title

    def test_full_parameterization(self, ethane):
        structure = ethane.to_parmed(title='ethane')
        parametrized = apply_forcefield(structure, forcefield='opls-aa', debug=False)

        assert sum((1 for at in parametrized.atoms if at.type == 'opls_135')) == 2
        assert sum((1 for at in parametrized.atoms if at.type == 'opls_140')) == 6
        assert len(parametrized.bonds) == 7
        assert all(x.type for x in parametrized.bonds)
        assert len(parametrized.angles) == 12
        assert all(x.type for x in parametrized.angles)
        assert len(parametrized.rb_torsions) == 9
        assert all(x.type for x in parametrized.dihedrals)


if __name__ == "__main__":
    test_class = TestOPLS()

    # mol = 'ethylbenzene'
    # top_path = test_class.find_topfile_by_mol_name(mol)
    # test_class.test_atomtyping(top_path, only_run=mol)

    test_class.find_correctly_implemented()
