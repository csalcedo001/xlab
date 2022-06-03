import pytest

from xlab.utils import merge_dicts
from xlab.cache import sort_args

@pytest.mark.parametrize(('a', 'b', 'r'), [
    ### No keys in common

    # Identity
    ({}, {}, {}),
    ({'a':0}, {}, {'a':0}),
    ({}, {'a':0}, {'a':0}),
    ({'a':0}, {'a':0}, {'a':0}),

    # Others
    ({'a':0, 'b':1}, {}, {'a':0, 'b':1}),
    ({'a':0}, {'b':1}, {'a':0, 'b':1}),
    ({}, {'a':0, 'b':1}, {'a':0, 'b':1}),


    ### Keys in common

    # Merge-order dependence
    ({'a':0, 'b':1}, {'a':1}, {'a':1, 'b':1}),
    ({'a':1, 'b':1}, {'a':0}, {'a':0, 'b':1}),
    ({'a':0, 'b':1}, {'a':1, 'b':1}, {'a':1, 'b':1}),
    ({'a':1, 'b':1}, {'a':0, 'b':1}, {'a':0, 'b':1}),
    ({'a':1}, {'a':0, 'b':1}, {'a':0, 'b':1}),
    ({'a':0}, {'a':1, 'b':1}, {'a':1, 'b':1}),

    # Multi-key tests
    (
        {'a':0, 'b':1., 'c':'x'},
        {'a':0, 'b':1., 'c':'x'},
        {'a':0, 'b':1., 'c':'x'}
    ),
    ({'a':[]}, {'a':[]}, {'a':[]}),
    ({'a':[0, 1, 2]}, {'a':[0, 1, 2]}, {'a':[0, 1, 2]}),
    ({'a':{'k':0}}, {'a':{'k':0}}, {'a':{'k':0}}),
    ({'a':{'k':0, 'q':1}}, {'a':{'k':0, 'q':1}}, {'a':{'k':0, 'q':1}}),
    ({'a':[{'k':0, 'q':1}]}, {'a':[{'k':0, 'q':1}]}, {'a':[{'k':0, 'q':1}]}),
    ({'a':0}, {'a':[1]}, {'a':[1]}),
    ({'a':0}, {'a':{'k':0}}, {'a':{'k':0}}),
    ({'a':0, 'b':1, 'c':2}, {'b':1, 'a':0, 'c':2}, {'a':0, 'b':1, 'c':2}),
    ({'a':0, 'b':1, 'c':2}, {'c':2, 'a':0, 'b':1}, {'a':0, 'b':1, 'c':2}),
    ({'a':[0, 1]}, {'a':[1, 0]}, {'a':[1, 0]}),

    ### Nested dicts

    # Identity
    ({'a':{'k':0, 'q':1}}, {'a':{}}, {'a':{'q':1, 'k':0}}),
    ({'a':{'k':0}}, {'a':{'q':1}}, {'a':{'q':1, 'k':0}}),
    ({'a':{}}, {'a':{'k':0, 'q':1}}, {'a':{'q':1, 'k':0}}),
    ({'a':{'k':0, 'q':1}}, {'a':{}}, {'a':{'q':1, 'k':0}}),

    ### Other tests
    
    (
        {'a':[{'k':0}, {'q':1}]},
        {'a':[{'q':1}, {'k':0}]},
        {'a':[{'q':1}, {'k':0}]}
    ),
    (
        {'a':{'k':[0], 'q':[1]}},
        {'a':{'q':[1], 'k':[0]}},
        {'a':{'q':[1], 'k':[0]}}
    ),
    (
        {'b':2, 'a':{'k':0, 'q':1}},
        {'a':{'q':1, 'k':0}, 'b':2},
        {'a':{'q':1, 'k':0}, 'b':2}
    ),
])
def test_get_hash(a, b, r):
    assert sort_args(merge_dicts(a, b)) == sort_args(r)