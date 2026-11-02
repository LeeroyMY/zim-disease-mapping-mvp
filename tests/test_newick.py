import unittest
import newick

class NewickParsingTestCase(unittest.TestCase):
    def test_newick_tree_leaves(self):
        tree_str = "(A:0.1,B:0.2,(C:0.3,D:0.4)E:0.5)F;"
        trees = newick.loads(tree_str)
        self.assertEqual(len(trees), 1)
        leaf_names = [leaf.name for leaf in trees[0].get_leaves()]
        self.assertEqual(leaf_names, ['A', 'B', 'C', 'D'])
