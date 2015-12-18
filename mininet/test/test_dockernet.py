import unittest
import os
import time
import subprocess
import docker
from mininet.net import Mininet
from mininet.node import Host, Controller
from mininet.node import UserSwitch, OVSSwitch, IVSSwitch
from mininet.topo import SingleSwitchTopo, LinearTopo
from mininet.log import setLogLevel
from mininet.util import quietRun
from mininet.clean import cleanup


class simpleTestTopology( unittest.TestCase ):
    """
        Helper class to do basic test setups.
        s1 -- s2 -- s3 -- ... -- sN
    """

    def __init__(self, *args, **kwargs):
        self.net = None
        self.s = []  # list of switches
        self.h = []  # list of hosts
        self.d = []  # list of docker containers
        self.docker_cli = None
        super(simpleTestTopology, self).__init__(*args, **kwargs)

    def createNet(
            self,
            nswitches=1, nhosts=0, ndockers=0,
            autolinkswitches=False):
        """
        Creates a Mininet instance and automatically adds some
        nodes to it.
        """
        self.net = Mininet( controller=Controller )
        self.net.addController( 'c0' )

        # add some switches
        for i in range(0, nswitches):
            self.s.append(self.net.addSwitch('s%d' % i))
        # if specified, chain all switches
        if autolinkswitches:
            for i in range(0, len(self.s) - 1):
                self.net.addLink(self.s[i], self.s[i + 1])
        # add some hosts
        for i in range(0, nhosts):
            self.h.append(self.net.addHost('h%d' % i))
        # add some dockers
        for i in range(0, ndockers):
            self.d.append(self.net.addDocker('d%d' % i, dimage="ubuntu"))

    def startNet(self):
        self.net.start()

    def stopNet(self):
        self.net.stop()

    def getDockerCli(self):
        """
        Helper to interact with local docker instance.
        """
        if self.docker_cli is None:
            self.docker_cli = docker.Client(
                base_url='unix://var/run/docker.sock')
        return self.docker_cli

    @staticmethod
    def setUp():
        pass

    @staticmethod
    def tearDown():
        cleanup()
        # make sure that all pending docker containers are killed
        with open(os.devnull, 'w') as devnull:
            subprocess.call(
                "sudo docker rm -f $(sudo docker ps -a -q)",
                stdout=devnull,
                stderr=devnull,
                shell=True)


class testDockernetConnectivity( simpleTestTopology ):

    def testHostDocker( self ):
        """
        d1 -- h1
        """
        # create network
        self.createNet(nswitches=0, nhosts=1, ndockers=1)
        # setup links
        self.net.addLink(self.h[0], self.d[0])
        # start Mininet network
        self.startNet()
        # check number of running docker containers
        assert(len(self.getDockerCli().containers()) == 1)
        # check connectivity by using ping
        assert(self.net.pingAll() <= 0.0)
        # stop Mininet network
        self.stopNet()

    def testDockerDocker( self ):
        """
        d1 -- d2
        """
        # create network
        self.createNet(nswitches=0, nhosts=0, ndockers=2)
        # setup links
        self.net.addLink(self.d[0], self.d[1])
        # start Mininet network
        self.startNet()
        # check number of running docker containers
        assert(len(self.getDockerCli().containers()) == 2)
        # check connectivity by using ping
        assert(self.net.pingAll() <= 0.0)
        # stop Mininet network
        self.stopNet()

    def testHostSwtichDocker( self ):
        """
        d1 -- s1 -- h1
        """
        # create network
        self.createNet(nswitches=1, nhosts=1, ndockers=1)
        # setup links
        self.net.addLink(self.h[0], self.s[0])
        self.net.addLink(self.d[0], self.s[0])
        # start Mininet network
        self.startNet()
        # check number of running docker containers
        assert(len(self.getDockerCli().containers()) == 1)
        # check connectivity by using ping
        assert(self.net.pingAll() <= 0.0)
        # stop Mininet network
        self.stopNet()

    def testDockerSwtichDocker( self ):
        """
        d1 -- s1 -- d2
        """
        # create network
        self.createNet(nswitches=1, nhosts=0, ndockers=2)
        # setup links
        self.net.addLink(self.d[0], self.s[0])
        self.net.addLink(self.d[1], self.s[0])
        # start Mininet network
        self.startNet()
        # check number of running docker containers
        assert(len(self.getDockerCli().containers()) == 2)
        # check connectivity by using ping
        assert(self.net.pingAll() <= 0.0)
        # stop Mininet network
        self.stopNet()

    def testDockerMultipleInterfaces( self ):
        """
        d1 -- s1 -- d2 -- s2 -- d3
        d2 has two interfaces, each with its own subnet
        """
        # create network
        self.createNet(nswitches=2, nhosts=0, ndockers=2)
        # add additional Docker with special IP
        self.d.append(self.net.addDocker(
            'd%d' % len(self.d), ip="11.0.0.2", dimage="ubuntu"))
        # setup links
        self.net.addLink(self.s[0], self.s[1])
        self.net.addLink(self.d[0], self.s[0])
        self.net.addLink(self.d[1], self.s[0])
        self.net.addLink(self.d[2], self.s[1])
        # special link that add second interface to d2
        self.net.addLink(
            self.d[1], self.s[1], params1={"ip": "11.0.0.1/8"})

        # start Mininet network
        self.startNet()
        # check number of running docker containers
        assert(len(self.getDockerCli().containers()) == 3)
        # check connectivity by using ping
        assert(self.net.ping([self.d[0], self.d[1]]) <= 0.0)
        assert(self.net.ping([self.d[2]], manualdestip="11.0.0.1") <= 0.0)
        assert(self.net.ping([self.d[1]], manualdestip="11.0.0.2") <= 0.0)
        # stop Mininet network
        self.stopNet()


if __name__ == '__main__':
    unittest.main()
