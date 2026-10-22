class ConfigurationException(Exception):
    pass


class TestSetupException(Exception):
    pass


class UninitialisedKafkaConsumerException(Exception):
    pass


class UninitialisedKafkaProducerException(Exception):
    pass
