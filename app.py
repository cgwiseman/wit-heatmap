from flask import Flask, request, redirect

from witbanner import banner

import operator
import html
import collections

app = Flask(__name__)

##############################################################################
##############################################################################

_DAYS = collections.OrderedDict()
_DAYS["M"] = "Monday"
_DAYS["T"] = "Tuesday"
_DAYS["W"] = "Wednesday"
_DAYS["R"] = "Thursday"
_DAYS["F"] = "Friday"

def _demo_search_time(slot):
	ampm = "am" if slot < 120 else "pm"
	slot -= 0 if slot < 130 else 120
	m = "30" if (slot / 5) % 2 is 1 else "00"
	h = slot / 10
	return "{}:{} {}".format(h, m, ampm)

def _demo_search_color(count, numprofs):
	if count is 0:
		return "white"
	elif count is 1:
		return "DarkGrey"
	elif count >= numprofs/2.:
		return "Red"
	else:
		return "Yellow"

def _demo_time_to_index(t, start):
    hrm,ampm = t.split(" ")
    hr,m = (int(x) for x in hrm.split(":"))
    isam = ampm=="am"

    index = hr
    if isam is False and hr < 12:
        index += 12

    index *= 10
    if m > 30:
        index += 5

    if not start:
        if m is 0:
            index -= 5

    return index

def _demo_facultyschedule(term, instructors, days):
    codes = banner.sectioncodes(term)
    profs = {name:code for code,name in codes["instructors"].items()}

    params = {"term":term,"subjects":codes["subjects"].keys()}
    params["instructors"] = [profs[p] for p in instructors]

    banner.termset(term)
    sections = banner.sectionsearch(**params)

    for section in sections:
        for classmtg in section["class"]:
            if classmtg[1].find("-") is not -1:
                tfrom,tto = classmtg[1].split("-")
                for day in (d for d in classmtg[0] if d in days):
                    for tf in range(_demo_time_to_index(tfrom, True), _demo_time_to_index(tto, False)+1, 5):
                        if tf>=80 and tf<200:
                            days[day][tf].add(section["instructor"])
                            
def _demo_studentschedule(term, students, days):
    banner.termset(term)
    
    for student in students:
        xyz = banner.getxyz_wid(term, student)
        banner.idset(xyz)
        
        schedule = banner.studentschedule()
        for entry in schedule:
            for meeting in entry["meetings"]:
                for day in meeting["days"]:
                    for tf in range(_demo_time_to_index(meeting["times"][0], True), _demo_time_to_index(meeting["times"][1], False)+1, 5):
                        if tf>=80 and tf<200:
                            days[day][tf].add(xyz)

def demo_schedule(term, instructors, students):
    days = {d:{t:set() for t in range(80, 200, 5)} for d in _DAYS.keys()}
    
    _demo_facultyschedule(term, instructors, days)
    _demo_studentschedule(term, students, days)
    
    return days

##############################################################################
##############################################################################

def _out(l):
    return "\n".join(l)
    
def _has_needed(l):
    for n in l:
        if n not in request.form:
            return False
    return True

def ssl(f):

    def wrapper(*args):
        if request.headers.get('X-Forwarded-Proto') == "http":
            return redirect(request.url.replace('http://', 'https://', 1), code=301)
        else:
            return f(*args)

    return wrapper

##############################################################################
##############################################################################

@ssl
@app.route('/', methods=['POST', 'GET'])
def login(msg=None):
    ret = []
    ret.append(str(request.headers.get('X-Forwarded-Proto')))
    if msg:
        ret.append('<b>{}</b>'.format(msg))
    ret.append('<form method="POST" action="term">')
    ret.append('Username: <input type="text" name="user" />')
    ret.append('<br />')
    ret.append('Password: <input type="password" name="pw" />')
    ret.append('<br />')
    ret.append('<input type="submit" />')
    ret.append('</form>')
    return _out(ret)

@ssl
@app.route('/term', methods=['POST'])
def term():
    ret = []
    if not _has_needed(("user","pw",)):
        return login()

    if not banner.init(u=request.form["user"], p=request.form["pw"], dieonfail=False):
        return login("Login failed!")
        
    ##

    finfo = banner.termform()
    ret.append('<form action="people" method="POST">')
    
    now = sorted(finfo["params"]["term"].items(), reverse=True)[0][0]
    ret.append('<select name="term">')
    for code,name in sorted(finfo["params"]["term"].items(), key=operator.itemgetter(1)):
        ret.append('<option {}value="{}">{}</option>'.format('selected="selected" ' if code==now else '', html.escape(code), html.escape(name)))
    ret.append('</select>')
    
    ret.append('<input type="hidden" name="sid" value="{}" />'.format(html.escape(banner.lastid())))
    ret.append('<input type="submit" value="submit" />')
    
    ret.append('</form>')
    
    return _out(ret)
    
@ssl
@app.route('/people', methods=['POST'])
def people():
    if not _has_needed(("sid","term",)):
        return login()
    
    if not banner.init(sid=request.form["sid"], dieonfail=False):
        return login("Bad session!")
    
    codes = banner.sectioncodes(request.form["term"])

    ret = []    
    ret.append('<form action="search" method="POST">')
    ret.append('<input type="hidden" name="term" value="{}" />'.format(request.form["term"]))
    
    ret.append('<h3>Faculty</h3>')
    ret.append('<select name="profs" multiple="multiple" size="20">')
    for code,name in sorted(codes["instructors"].items(), key=operator.itemgetter(1)):
        ret.append('<option value="{}">{}</option>'.format(html.escape(name), html.escape(name)))
    ret.append('</select>')
    ret.append('<br />')
    
    ret.append('<h3>W-Numbers (separated by whitespace)</h3>')
    ret.append('<textarea name="students" rows="20" cols="50">')
    ret.append('</textarea>')
    
    ret.append('<br /><br />')
    
    ret.append('<input type="hidden" name="sid" value="{}" />'.format(html.escape(banner.lastid())))
    ret.append('<input type="submit" value="submit" />')
    
    ret.append('</form>')
    
    return _out(ret)

@ssl
@app.route('/search', methods=['POST'])
def search():
    if not _has_needed(("sid","term","profs","students",)):
        return login()
        
    if not banner.init(sid=request.form["sid"], dieonfail=False):
        return login("Bad session!")
    
    profslist = request.form.getlist("profs")
    studentslist = request.form["students"].split()
    
    days = demo_schedule(request.form["term"], profslist, studentslist)
    num = len(profslist) + len(studentslist)
    
    day_names = list(days.keys())
    slot_names = sorted(days[day_names[0]].keys())
    
    ret = []
    
    ret.append('<h1>Heatmap</h1>')
    ret.append('<p><a href="/">Start Again</a></p>')
    if profslist:
        ret.append('<h2>Faculty ({}): '.format(len(profslist)) + html.escape('; '.join(profslist)) + '</h2>')
        
    if studentslist:
        ret.append('<h2>Students ({}): '.format(len(studentslist)) + html.escape('; '.join(studentslist)) + '</h2>')
        
    ret.append('<table border="1">')
    
    ret.append('<tr>')
    ret.append('<th style="width: 80px"></th>')
    for d,name in _DAYS.items():
        ret.append('<th style="width: 80px">{}</th>'.format(html.escape(name)))
    ret.append('</tr>')
    
    for slot in slot_names:
        ret.append('<tr>')
        ret.append('<th>{}</th>'.format(html.escape(_demo_search_time(slot))))
        for d in _DAYS.keys():
            count = len(days[d][slot])
            ret.append('<td style="text-align: center; background-color: {}">{}</td>'.format(_demo_search_color(count, num), html.escape(str(count) if count > 0 else "")))
        ret.append('</tr>')
    
    ret.append('</table>')
    
    return _out(ret)

##############################################################################
##############################################################################

if __name__ == '__main__':
    app.run()
