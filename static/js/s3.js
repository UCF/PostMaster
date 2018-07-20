(function() {
  'use strict';

var creds = {
  bucket: 'web.ucf.edu',
  folder: 'email',
  accessKey: 'AKIAIJIGOEVN46JWNBJA',
  secretKey: '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'
};

// Configure The S3 Object
AWS.config.update({
  accessKeyId: creds.accessKey,
  secretAccessKey: creds.secretKey
});
AWS.config.region = 'us-east-1';

var aws = new AWS.S3();

function getFileList(callback, list) {
  var params = {
    Bucket: creds.bucket,
    Prefix: creds.folder
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
      if(filenameArry[2] && filenameArry[2].startsWith("2018-")) {
        $list.append('<a class="list-group-item list-group-item-action" href="#" data-url="https://s3.amazonaws.com/' + creds.bucket + '/' + fileList[i].Key + '">' + filenameArry[2] + '</a>');
      }
    }
    if($list.find('a').length === 0) {
      $list.append('No items available at this time.');
    }
  }
};

function init() {
  getFileList(printFileList, '2018');
}

// TODO: Set this to only load when modal is opened

$(init);

}());
