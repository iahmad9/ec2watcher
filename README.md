# List Unused Machines on AWS EC2

Note: In below text, term instance and machine is used interchangebly

### How to Use:
This standlone python based tool can be used to list the number of unused/under utilized instances on AWS EC2 cloud for the given account. script can be run from command line or could be integrated with jenkins by importing the jenkins-job.xml

To run from command line

    $ python ec2_watcher.py --key-id <aws_access_key_id>
                                         --key-secret <aws_secret_access_key>
                                         --region-name us-east-1
                                         --period 1
                                         --duration 24
                                         --threshold 2

This will generate basic html report.html with a table, listing the unused machines with their IDs and Public DNS Name.

For more details about command line options, run

    $ python ec2_watcher.py --help

**Dependencies**:
* Python 2.7 +
* boto3

Module level dependencies can be installed via pip

    $ pip3 install -r requirements.txt

### Jenkins Setup:

To seutp the jenkins job, use jenkins client to create jenkins job from jenkins-job.xml, which should appear as parameterized job in jenkins web interface. Once the job is imported successfully, following needs to be configured: 
* setup the aws credentials, by adding AWS_KEY_ID and AWS_KEY_SECRET credentials in jenkin's credential interface for the user jenkins. This is to avoid showing the credentials in plain text in build log/console output
* To run with custom filtering criteria, on Build with Paramters page, following variables can be configured
    * AWS_REGION_NAME
    * PERIOD
    * DURATION
    * THRESHOLD

By default job would run every morning at 8AM Madrid Time and produce a basic html report, which can be seen by following HTML Report link on jobs detail page.

### Assumptions:
* Usage of instance is measured based on its average cpu usage percentage for given time frame
* To qualify a machine in use, it should be accessed/used in such a way that its cpu utilization takes it above the given threshold for the given period (agregatted) over the specified duration
* For now, no other metric is used to assess the work load
* There can be any number of machines
* Currently, it doesn't take into account that usage could be low on weekends, public holidays etc
* Currently, there is no upper limit to specify the period, duration, threshold.
* Minimum granularity of sampling (period) is 1 hour
* If instance age is less than the spcified start time (current time - duration), then this instance usage won't be measured
* For single run of the script, only one aws account can be monitored

### Potential Improvements:
There can be number of improvements made to improve the overall tool design and functionality e.g.
* CloudWatch could be separate class which can then monitor different type of resources e.g. EC2, EBS etc
* Filtering configuration could be defined in external configuration file e.g. yaml file
* Instead of polling the usage, aws lambda functions could be used to trigger the events/jenkins job to alert about usage pattern of resources
* There should be more way to define the filter e.g. based on disk read/write, network usage, volume idle time etc.
* HTML reporting could be replaced with more , it should be chart/graphed based reporting, giving the overall trend of resource usage over a period of time, which could help with decsion making about where the cost could be saved.
* Additional output parameter can be added to specify the custom report name
* Adding limits for the period, duration, threshold parameters
* Taking into account low usage over public holidays
* Parameters extensive validity checking
* Error handling
* It doesn't take into account api rate limit, or response size at the moment
