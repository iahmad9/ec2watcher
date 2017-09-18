#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
            List Unused Machines on AWS/EC2.

This is a tool to list the unused or under utilized machines as per
the given criteria. This tool can be run from command line by providing
account and criteria information. For now, it generates a basic html
report with list of machines based on their average cpu utilization
percentage against the provided threshold.

Example:

        $ python list-unused-machines.py --key-id <aws_access_key_id>
                                         --key-secret <aws_secret_access_key>
                                         --region-name us-east-1
                                         --period 1
                                         --duration 24
                                         --threshold 2

This will list all the machines on given account whose average cpu usage in
last 24 hours is less than 2 percent, with sampling period of 1 hour

"""
from __future__ import print_function
import datetime
import xml.etree.cElementTree as ET
from argparse import ArgumentParser, RawTextHelpFormatter
from boto3 import session
from botocore.exceptions import ClientError

class EC2CloudWatcher(object):
    """ Class to interact with cloudwatch and EC2 AWS services"""

    def __init__(self, key_id, key_secret, region_name,
                 period=3600, duration=24*3600, threshold=1.0):
        """ Class object initializer

        Args:
        key_id (str): aws_access_key_id from aws account
        key_secret (str): aws_secret_access_key from aws account
        region_name (str): region_name from aws account
        period (int): cloudwatch sampling period in seconds
        duration (int): time in seconds to calculate start time
        threshold (int): cpu threshold in percentage
        """
        if not key_id:
            raise ValueError("Invalid Key ID")
        if not key_secret:
            raise ValueError("Invalid Key Secret")
        if not region_name:
            raise ValueError("Invalid Region Name")

        self.period = period
        self.duration = duration
        self.threshold = threshold

        self._session = session.Session(aws_access_key_id=key_id,
                                        aws_secret_access_key=key_secret,
                                        region_name=region_name)
        self._ec2 = self._session.resource('ec2')
        self._cw = self._session.client('cloudwatch')


    def get_average_meteric(self, start_time, metric_name, namespace, dimensions):
        """ Get the average meteric in percentage for the given meteric name

        Args:
            start_time (datetime): Time from when the meteric should be calculated
                                    until the current time
            meteric_name (str): cloudwatch meteric name
            namespace (str): cloudwatch namespace
            dimensions (str): cloudwatch dimension matrix
        """
        response = None
        try:
            response = self._cw.get_metric_statistics(
                Period=self.period,
                StartTime=start_time,
                EndTime=datetime.datetime.utcnow(),
                MetricName=metric_name,
                Namespace=namespace,
                Statistics=['Average'],
                Unit='Percent',
                Dimensions=[dimensions]
            )
        except ClientError as clienterror:
            print (clienterror)
        return response

    def get_average_cpu_utilization(self, instance_id):
        """ Get average cpu utilization for the given Instance ID

        Args:
            instance_id (dict): EC2 Instance ID

            return: Returns the dict response recieved from cloudwatcher
        """
        start_time = datetime.datetime.utcnow() - datetime.timedelta(seconds=self.duration)
        dimensions = {"Name":"InstanceId", "Value":instance_id}
        response = self.get_average_meteric(start_time, "CPUUtilization", "AWS/EC2", dimensions)
        return response

    def is_used(self, instance):
        """ Check if given instance is in use

        TODO - This function can be expaned to check for other meterics
        before concluding if a mchine is in use or not

        Args:
            instance (dict): Instance id to Check
            return (bool): Returns True if in use, False otherwise
        """
        launch_time = instance.launch_time
        start_time = datetime.datetime.now(launch_time.tzinfo)-datetime.timedelta(seconds=self.duration)        
        if launch_time < start_time:
            return True

        response = self.get_average_cpu_utilization(instance.id)
        datapoints = response['Datapoints']
        averages = [d['Average'] for d in datapoints]
        if any(a > self.threshold for a in averages):
            return True
        return False

    def get_unused_machines(self):
        """ Loop through each instance on EC2 for the account and
        check if it is in use or not

        Args:
            returns: List of instances marked as unused
        """
        machines = []
        for instance in self._ec2.instances.all():            
            if self.is_used(instance):
                continue # This machine is in use, check the next one
            # Reached here, machine is unused as per given criteria, add it to the list
            machines.append(instance)
        return machines


def write_basic_html_report(machines, criteria):
    """ Write basic html report with a table listing down the given
    machines
    Args:
        machines (list): list of machines to add to the report
        criteria (str): criteria information used to filter the unused machines
    """
    info_header = "Following information is used to check for the unused machines"
    root = ET.Element('html')
    para = ET.SubElement(root, 'p')
    para.text = info_header
    para = ET.SubElement(root, 'p')
    para.text = criteria
    table = ET.SubElement(root, 'table')
    table.attrib['border'] = '1'
    tr = ET.SubElement(table, 'tr')
    th = ET.SubElement(tr, 'th')
    th.text = 'Instance ID'
    th = ET.SubElement(tr, 'th')
    th.text = 'Public DNS Name'
    for m in machines:
        tr = ET.SubElement(table, 'tr')
        td = ET.SubElement(tr, 'td')
        td.text = m.id
        td = ET.SubElement(tr, 'td')
        td.text = m.public_dns_name

    tree = ET.ElementTree(root)
    tree.write('report.html')

   
def main():
    parser = ArgumentParser(description=__doc__, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--key-id', type=str, nargs='?',
                        help='key id from AWS account', required=True)
    parser.add_argument('--key-secret', type=str, nargs='?',
                        help='key secret from AWS account', required=True)
    parser.add_argument('--region-name', type=str, nargs='?',
                        help='region name from AWS account', default='us-east-1')
    parser.add_argument('--period', type=int, nargs='?',
                        help="""Sampling period for metric calucation in hours,
                        default: 1 hour, max: 24 hours""", default=1)
    parser.add_argument('--duration', type=int, nargs='?',
                        help="""Duration over which machine usage is monitored
                        in hours, default: 24 hours, max: 72 hours""", default=24)
    parser.add_argument('--threshold', type=int, nargs='?',
                        help='Average CPU uitilization to check, default is 1 %%, max: 100 %%', default=1)
    args = parser.parse_args()


    if args.period < 1 or args.period > 24:
        print ("Period value should be between 1 and 24 hours")
        return 1

    if args.duration < 1 or args.duration > 72:
        print ("Duration value should be between 1 and 72 hours")
        return 1

    if args.threshold < 1 or args.threshold > 100:
        print ("Threshold value should be between 1 and 100")
        return 1

    try:
        wathcer = EC2CloudWatcher(args.key_id,
                                  args.key_secret,
                                  args.region_name,
                                  args.period*3600,
                                  args.duration*3600,
                                  args.threshold)
        machines = wathcer.get_unused_machines()
    except Exception as exception:
        print(exception)

    criteria = """region_name:{0},
                  sampling period:{1} hours,
                  duration:{2} hours,
                  cpu threshold: {3}""".format(
                      args.region_name,
                      args.period,
                      args.duration,
                      args.threshold)
    write_basic_html_report(machines, criteria)

if __name__ == '__main__':
    main()
