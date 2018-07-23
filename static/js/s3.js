(function() {
  'use strict';

  var aws_creds,
      aws;

  function getFileList(callback, list) {
    var params = {
      Bucket: aws_creds.bucket,
      Prefix: aws_creds.folder
    };

    aws.listObjectsV2(params, function(err, data) {
      if (err) {
        callback({ error: true });
        console.log(err, err.stack);
      } else {
        callback(data.Contents, list);
      }
    });
  }

  var printFileList = function(fileList, list) {
    var $list = $('.templates');
    if(fileList.error) {
      $list.append('Error Retrieving files.');
    } else {
      for (var i in fileList) {
        var filenameArry = fileList[i].Key.split("/");
        if(filenameArry[2] && filenameArry[2].startsWith(list + "-")) {
          $list.append('<a class="list-group-item list-group-item-action" href="#" data-url="https://s3.amazonaws.com/' + aws_creds.bucket + '/' + fileList[i].Key + '">' + filenameArry[2] + '</a>');
        }
      }
      if($list.find('a').length === 0) {
        $list.append('No items available at this time.');
      }
    }
  };

  function init() {
    aws_creds = getAWSCreds();
    aws_creds.folder = 'email';

    // Configure The S3 Object
    AWS.config.update({
      accessKeyId: aws_creds.accessKey,
      secretAccessKey: aws_creds.secretKey
    });
    AWS.config.region = 'us-east-1';

    aws = new AWS.S3();

    getFileList(printFileList, '2018');
  }

  $(init);

}());
