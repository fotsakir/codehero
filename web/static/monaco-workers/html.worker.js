self.MonacoEnvironment = {
    baseUrl: self.location.origin + '/static/monaco/min/'
};
importScripts(self.location.origin + '/static/monaco/min/vs/base/worker/workerMain.js');
