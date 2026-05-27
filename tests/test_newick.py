import newick

tree_str = "(A:0.1,B:0.2,(C:0.3,D:0.4)E:0.5)F;"
trees = newick.loads(tree_str)
for tree in trees:
    for leaf in tree.get_leaves():
        print(leaf.name)
