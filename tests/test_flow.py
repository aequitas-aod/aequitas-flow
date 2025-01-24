import unittest
from flow import Site, SiteQuery, Channel, Network

class TestSite(unittest.TestCase):
    def setUp(self):
        self.network = Network()

    def test_site_creation(self):
        site = Site(self.network, "Site A")
        self.assertEqual(site.label, "Site A")
        self.assertIsInstance(site, Site)

    def test_site_group_creation(self):
        site1 = Site(self.network, "Site A")
        site2 = Site(self.network, "Site B")
        site_group = Site(self.network, site1, site2)
        self.assertIn((site1.id, site1), site_group._sites)
        self.assertIn((site2.id, site2), site_group._sites)

    def test_invalid_site_creation(self):
        with self.assertRaises(AttributeError):
            Site(self.network, 123)

class TestSiteQuery(unittest.TestCase):
    def setUp(self):
        self.network = Network()
        self.site1 = Site(self.network, "Site A")
        self.site2 = Site(self.network, "Site B")
        self.site_query = SiteQuery([self.site1, self.site2])

    def test_label_filter(self):
        filtered_query = self.site_query.label("Site A")
        self.assertIn(self.site1, list(filtered_query))
        self.assertNotIn(self.site2, list(filtered_query))

    def test_length(self):
        self.assertEqual(len(self.site_query), 2)

    def test_indexing(self):
        self.assertEqual(self.site_query[0], self.site1)

class TestChannel(unittest.TestCase):
    def setUp(self):
        self.network = Network()
        self.site1 = Site(self.network, "Source Site")
        self.site2 = Site(self.network, "Target Site")
        self.channel = Channel(self.network, self.site1, self.site2)

    def test_channel_creation(self):
        self.assertIn(self.site1, self.channel._source)
        self.assertIn(self.site2, self.channel._target)

    def test_add_input(self):
        new_site = Site(self.network, "New Source")
        self.channel.add_input(new_site)
        self.assertIn(new_site, self.channel._source)

    def test_add_output(self):
        new_site = Site(self.network, "New Target")
        self.channel.add_output(new_site)
        self.assertIn(new_site, self.channel._target)

    def test_discard_input(self):
        self.channel.discard_input(self.site1)
        self.assertNotIn(self.site1, self.channel._source)

    def test_discard_output(self):
        self.channel.discard_output(self.site2)
        self.assertNotIn(self.site2, self.channel._target)

class TestNetwork(unittest.TestCase):
    def setUp(self):
        self.network = Network()

    def test_site_creation(self):
        site = self.network.site("Site A", create=True)
        self.assertIn(site.id, self.network._sites)

    def test_channel_creation(self):
        site1 = self.network.site("Site A", create=True)
        site2 = self.network.site("Site B", create=True)
        channel = self.network.channel(site1, site2)
        self.assertIn(channel.id, self.network._channels)

    def test_compute_level(self):
        site1 = self.network.site("Site A", create=True)
        site2 = self.network.site("Site B", create=True)
        channel = self.network.channel(site1, site2)
        self.network.compute_order()
        self.assertEqual(site1._level, 0)
        self.assertEqual(channel._level, 0)
        self.assertEqual(site2._level, 1)

    def test_orphaned_sites(self):
        site1 = self.network.site("Orphaned Site", create=True)
        self.network.compute_order()
        self.assertEqual(site1._level, -1)

if __name__ == "__main__":
    unittest.main()
