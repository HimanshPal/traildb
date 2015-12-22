from itertools import combinations, chain
from collections import Counter
import unittest
import hashlib
import shutil

from traildb import TrailDBConstructor

class TestFilterSetter(unittest.TestCase):
    fields = ['a', 'b', 'c']

    def setUp(self):
        cookie = hashlib.md5('a').hexdigest()
        cons = TrailDBConstructor('test.tdb', self.fields)
        for i in range(100):
            cons.add(cookie,
                     123 + i,
                     ['%s%d' % (f, i) for f in self.fields])
        self.tdb = cons.finalize()

    def test_empty_filter(self):
        self.assertEquals(self.tdb.get_filter(), [])

    def test_simple_filter(self):
        q = [[{'field' : 'a', 'value' : 'a1', 'op' : 'equal'}]]
        self.tdb.set_filter(q)
        self.assertEquals(self.tdb.get_filter(), q)

    def test_simple_filter_missing_field(self):
        q = [[{'field' : 'z', 'value' : 'a1', 'op' : 'equal'}]]
        self.tdb.set_filter(q)
        self.assertEquals(self.tdb.get_filter(), [[False]])

    def test_many_filters(self):
        for c in range(1, len(self.fields) + 1):
            for fields in combinations(self.fields, c):
                q = [[{'value': '%s%d' % (f, i) , 'field' : f, 'op' : 'equal'} for i in range(10)]
                     for f in fields]

                q += [[{'op': 'notequal', 'field' : f, 'value': '%s%d' % (f, i)}
                           for i in range(10)]
                      for f in fields]
                self.tdb.set_filter(q)
                self.assertEquals(self.tdb.get_filter(), q)

    def tearDown(self):
        shutil.rmtree('test.tdb', True)

class TestFilterDecode(unittest.TestCase):
    fields = ['a', 'b', 'c']

    def setUp(self):
        self.stats = Counter()
        cons = TrailDBConstructor('test.tdb', self.fields)
        for cookie_id in range(100):
            cookie = hashlib.md5(str(cookie_id)).hexdigest()
            for i in range((cookie_id % 10) + 1):
                events = ['%s%d' % (f, i) for f in self.fields]
                cons.add(cookie, 123 + i, events)
                self.stats.update(events)

        self.tdb = cons.finalize()

    def test_one_term(self):
        for field_id, field in enumerate(self.fields):
            for i in range(10):
                key = '%s%d' % (field, i)
                self.tdb.set_filter([[{'field' : field, 'value' : key}]])
                found = 0
                for cookie, trail in self.tdb.crumbs():
                    for event in trail:
                        self.assertEquals(event[field_id + 1], key)
                        found += 1
                self.assertEquals(found, self.stats[key])

    def test_one_negative_term(self):
        for field_id, field in enumerate(self.fields):
            for i in range(10):
                key = '%s%d' % (field, i)
                self.tdb.set_filter([[{'field' : field,
                                       'op': 'notequal',
                                       'value': key}]])

                stats = Counter()
                for cookie, trail in self.tdb.crumbs():
                    for event in trail:
                        self.assertNotEquals(event[field_id + 1], key)
                        stats.update([event[field_id + 1]])

                correct = {f: v for f, v in self.stats.iteritems()
                           if f != key and f[0] == key[0]}
                self.assertEquals(stats, correct)

    def test_missing_field(self):

        num_items_nf = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
        self.assertTrue(num_items_nf > 0)

        q = [
                [{'field' : 'z', 'value' : 'test'}]
            ]
        self.tdb.set_filter(q)
        num_items = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
        self.assertEquals(num_items, 0)

        q = [
                [{'field' : 'z', 'value' : ''}]
            ]
        self.tdb.set_filter(q)
        num_items = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
        self.assertEquals(num_items, num_items_nf)

        q = [
                [{'field' : 'z', 'value' : '', 'op' : 'notequal'}]
            ]
        self.tdb.set_filter(q)
        num_items = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
        self.assertEquals(num_items, 0)

    def test_missing_field_conjunction(self):
        for i in range(9):
            q = [[{'field' : 'a', 'value' : 'a%d' % i}]]
            self.tdb.set_filter(q)
            num_items_nf = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
            self.assertTrue(num_items_nf > 0)
            self.tdb.set_filter(q + [[{'field' : 'z', 'value' : 'test'}]])
            num_items = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
            self.assertEquals(num_items, 0)
            self.tdb.set_filter(q + [[{'field' : 'z', 'value' : ''}]])
            num_items = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
            self.assertEquals(num_items, num_items_nf)
            self.tdb.set_filter(q + [[{'field' : 'z', 'value' : '', 'op' : 'notequal'}]])
            num_items = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
            self.assertEquals(num_items, 0)
            self.tdb.set_filter(q + [[{'field' : 'z', 'value' : 'test', 'op' : 'notequal'}]])
            num_items = sum([len(trail) for cookie, trail in self.tdb.crumbs()])
            self.assertEquals(num_items, num_items_nf)

    def test_disjunction(self):
        for i in range(9):
            q = {f: ['%s%d' % (f, i), '%s%d' % (f, i + 1)]
                 for f in self.fields}

            fltr = [[{'field' : f, 'value' : v}
                        for f in q for v in q[f]]]
            self.tdb.set_filter(fltr)
            stats = Counter()
            for cookie, trail in self.tdb.crumbs():
                for event in trail:
                    for f, field in enumerate(self.fields):
                        self.assertTrue(event[f + 1] in q[field])
                        stats.update([event[f + 1]])
            for key in chain(*q.values()):
                self.assertEquals(stats[key], self.stats[key])

    def test_conjunction(self):
        for c in range(2, len(self.fields) + 1):
            for fields in combinations(self.fields, c):
                for i in range(10):
                    q = [[{'field' : f, 'value' : '%s%d' % (f, i)}] for f in fields]

                    self.tdb.set_filter(q)
                    stats = Counter()
                    for cookie, trail in self.tdb.crumbs():
                        for event in trail:
                            for f, field in enumerate(self.fields):
                                self.assertTrue(event[f + 1], '%s%d' % (field, i))
                                stats.update([event[f + 1]])
                    for f in q:
                        key = f[0]['value']
                        self.assertEquals(stats[key], self.stats[key])

    def test_impossible_conjunction(self):
        for i in range(9):
            q = [[{'field' : f, 'value' : '%s%d' % (f, i + j)}]
                 for j, f in enumerate(self.fields)]

            self.tdb.set_filter(q)
            impossible = True
            for cookie, trail in self.tdb.crumbs():
                for event in trail:
                    impossible = False
            self.assertTrue(impossible)

    def test_conjunction_of_disjunctions(self):
        for fields in combinations(self.fields, 2):
            q = [{fields[0]: ['%s%d' % (fields[0], i) for i in range(2,5)]},
                 {fields[1]: ['%s%d' % (fields[1], i) for i in range(2,5)]}]

            fltr = [[{'field' : f, 'value' : v} for v in c[f]]
                        for c in q for f in c]
            self.tdb.set_filter(fltr)
            stats = Counter()
            for cookie, trail in self.tdb.crumbs():
                for event in trail:
                    for f, field in enumerate(fields):
                        self.assertTrue(getattr(event, field) in q[f][field])
                        stats.update([getattr(event, field)])
            num = 0
            for f in q:
                for key in f.values()[0]:
                    num += 1
                    self.assertEquals(stats[key], self.stats[key])
            self.assertTrue(num, len(stats))

    def tearDown(self):
        shutil.rmtree('test.tdb', True)


class TestFilterEdgeEncoded(unittest.TestCase):
    fields = ['f1', 'f2']
    data = [('a', 'x0'), ('a', 'x1'), ('a', 'x0'), ('a', 'x0'), ('a', 'x1'),
            ('b', 'x0'), ('b', 'x1'), ('b', 'x0'), ('b', 'x0'), ('b', 'x1'), ('b', 'x1')]

    def setUp(self):
        cons = TrailDBConstructor('test.tdb', self.fields)
        for i, event in enumerate(self.data):
            cons.add('a' * 32, 123 + i, event)
        self.tdb = cons.finalize()

    def test_simple_filter(self):
        q = [[{'field' : 'f2', 'value' : 'x0'}]]
        stats = Counter()
        res = self.tdb.trail(0, filter_expr=q, edge_encoded=True)
        for _time, event in res:
            stats.update(event.itervalues())
        self.assertEquals(len(res), 6)
        self.assertEquals(stats, {'x0': 4, 'a': 1, 'b': 1})

    def test_disjunction(self):
        q = [[{'field' : 'f2', 'value' : 'x0'},
              {'field' : 'f2', 'value' : 'x1'}]]
        stats = Counter()
        res = self.tdb.trail(0, filter_expr=q, edge_encoded=True)
        for _time, event in res:
            stats.update(event.itervalues())
        self.assertEquals(len(res), len(self.data))
        self.assertEquals(stats, {'a': 1, 'b': 1, 'x0': 4, 'x1': 4})

    def test_negative(self):
        q = [[{'field' : 'f1', 'value': 'a', 'op': 'notequal'}]]
        stats = Counter()
        res = self.tdb.trail(0, filter_expr=q, edge_encoded=True)
        for _time, event in res:
            stats.update(event.itervalues())
        self.assertEquals(len(res), 6)
        self.assertEquals(stats, {'b': 1, 'x0': 2, 'x1': 2})

    def test_conjunction(self):
        q = [[{'field' : 'f2', 'value' : 'x1' }],
             [{'field' : 'f1', 'value' : 'b'}]]
        stats = Counter()
        res = self.tdb.trail(0, filter_expr=q, edge_encoded=True)
        for _time, event in res:
            stats.update(event.itervalues())
        self.assertEquals(len(res), 3)
        self.assertEquals(stats, {'b': 1, 'x1': 2})

    def test_impossible_conjunction(self):
        q = [[{'field':'f2', 'value' :'x0'}],
             [{'field':'f2', 'value' :'x1'}]]
        stats = Counter()
        res = self.tdb.trail(0, filter_expr=q, edge_encoded=True)
        for _time, event in res:
            stats.update(event.itervalues())
        self.assertEquals(len(res), 0)
        self.assertEquals(stats, {})

    def tearDown(self):
        shutil.rmtree('test.tdb', True)

if __name__ == '__main__':
    unittest.main()
