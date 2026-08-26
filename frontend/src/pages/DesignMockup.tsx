import React, { useState } from 'react';
const IconPlaceholder = ({ className }: { className?: string }) => (
  <svg className={className || 'w-4 h-4'} fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" /></svg>
);
const Search = IconPlaceholder;
const LayoutDashboard = IconPlaceholder;
const Clock = IconPlaceholder;
const ListTodo = IconPlaceholder;
const TrendingUp = IconPlaceholder;
const Calculator = IconPlaceholder;
const FileText = IconPlaceholder;
const Briefcase = IconPlaceholder;
const Calendar = IconPlaceholder;
const ImageIcon = IconPlaceholder;
const Users = IconPlaceholder;
const MapPin = IconPlaceholder;
const BarChart2 = IconPlaceholder;
const Settings = IconPlaceholder;
const LogOut = IconPlaceholder;
const Globe = IconPlaceholder;
const ChevronDown = IconPlaceholder;
const FileSpreadsheet = IconPlaceholder;
const Edit = IconPlaceholder;
const ArrowUpRight = IconPlaceholder;
const ArrowDownRight = IconPlaceholder;
const CheckCircle2 = IconPlaceholder;
const CircleDashed = IconPlaceholder;

export default function ConstructionDashboard() {
  const [activeMenu, setActiveMenu] = useState('Invoices');

  const menuItems = [
    { name: 'Dashboard', icon: LayoutDashboard },
    { name: 'Time Tracking', icon: Clock },
    { name: 'Task List', icon: ListTodo },
    { name: 'Lead Pipeline', icon: TrendingUp },
    { name: 'Estimates', icon: Calculator },
    { name: 'Invoices', icon: FileText },
    { name: 'Projects', icon: Briefcase },
    { name: 'Schedule', icon: Calendar, badge: 'New' },
    { name: 'Photos & Files', icon: ImageIcon },
    { name: 'Customers', icon: Users },
    { name: 'Map', icon: MapPin },
    { name: 'Reports', icon: BarChart2 },
  ];

  const tableData = [
    { id: '2501130', name: 'Albert Flores', email: 'rian@yandex.ru', value: '$ 2,084', balance: '$ 8,264', status: 'Accepted', date: '10/12/2022' },
    { id: '2501131', name: 'Ronald Richards', email: 'qamaha@mail.ru', value: '$ 2,084', balance: '$ 8,264', status: 'Overdue', date: '10/12/2022' },
    { id: '2501132', name: 'Jane Cooper', email: 'imabela@gmail.com', value: '$ 2,084', balance: '$ 8,264', status: 'Pending', date: '10/12/2022' },
    { id: '2501133', name: 'Brooklyn Simmons', email: 'mijakota@mail.ru', value: '$ 2,084', balance: '$ 8,264', status: 'Overdue', date: '10/12/2022' },
    { id: '2501134', name: 'Marvin McKinney', email: 'line@yandex.ru', value: '$ 2,084', balance: '$ 8,264', status: 'Pending', date: '10/12/2022' },
    { id: '2501135', name: 'Darrell Steward', email: 'warn@mail.ru', value: '$ 2,084', balance: '$ 8,264', status: 'Accepted', date: '10/12/2022' },
  ];

  const getStatusColor = (status: string) => {
    switch(status) {
      case 'Accepted': return 'text-emerald-600 bg-emerald-50';
      case 'Overdue': return 'text-rose-600 bg-rose-50';
      case 'Pending': return 'text-amber-600 bg-amber-50';
      default: return 'text-slate-600 bg-slate-50';
    }
  };

  return (
    <div className="flex h-screen bg-slate-50 font-sans text-slate-800 overflow-hidden">
      
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-100 flex flex-col h-full overflow-y-auto shrink-0">
        <div className="p-6 flex items-center gap-3">
          <div className="w-8 h-8 rounded border border-slate-200"></div>
          <div>
            <h1 className="font-bold text-sm tracking-wide text-slate-900 leading-tight">CONSTRUCTION</h1>
            <p className="text-[10px] font-semibold text-slate-400 tracking-wider">SERVICE</p>
          </div>
        </div>

        <div className="px-6 mb-6">
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input 
              type="text" 
              placeholder="Search" 
              className="w-full pl-9 pr-4 py-2 bg-slate-50 border-none rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-teal-500/20"
            />
          </div>
        </div>

        <div className="px-6 mb-2">
          <p className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">Main Menu</p>
        </div>

        <nav className="flex-1 px-4 space-y-0.5">
          {menuItems.map((item) => (
            <button
              key={item.name}
              onClick={() => setActiveMenu(item.name)}
              className={`w-full flex items-center justify-between px-3 py-2.5 rounded-lg transition-colors ${
                activeMenu === item.name 
                  ? 'bg-slate-50 text-teal-700 font-medium' 
                  : 'text-slate-500 hover:bg-slate-50 hover:text-slate-700'
              }`}
            >
              <div className="flex items-center gap-3">
                <item.icon className={`w-4 h-4 ${activeMenu === item.name ? 'text-teal-600' : ''}`} />
                <span className="text-sm">{item.name}</span>
              </div>
              {item.badge && (
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-amber-400 text-amber-900">
                  {item.badge}
                </span>
              )}
            </button>
          ))}
        </nav>

        <div className="p-4 mt-auto border-t border-slate-100 space-y-1">
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-500 hover:bg-slate-50 rounded-lg">
            <Settings className="w-4 h-4" /> Settings
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2 text-sm text-slate-500 hover:bg-slate-50 rounded-lg">
            <LogOut className="w-4 h-4" /> Logout
          </button>
          <button className="w-full flex items-center justify-between px-3 py-2 mt-2 text-sm text-slate-500 hover:bg-slate-50 rounded-lg border border-slate-100">
            <div className="flex items-center gap-2">
              <Globe className="w-4 h-4" /> Eng
            </div>
            <ChevronDown className="w-4 h-4" />
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full overflow-hidden">
        {/* Header */}
        <header className="h-20 bg-white flex items-center justify-between px-8 border-b border-slate-100 shrink-0">
          <h2 className="text-xl font-semibold text-slate-800">Customers details</h2>
          
          <div className="flex items-center gap-4">
            <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50">
              <Calendar className="w-4 h-4 text-slate-400" />
              9/12/2022 - 9/8/2022
            </button>
            <div className="h-6 w-px bg-slate-200"></div>
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-teal-600 hover:bg-teal-50 rounded-lg">
              <FileSpreadsheet className="w-4 h-4" /> VIEW STATEMENT
            </button>
            <button className="flex items-center gap-2 px-3 py-2 text-sm font-semibold text-teal-600 hover:bg-teal-50 rounded-lg">
              <Edit className="w-4 h-4" /> EDIT CUSTOMERS DETAILS
            </button>
            <div className="w-10 h-10 rounded-full bg-slate-200 border-2 border-white shadow-sm ml-2 overflow-hidden">
              <img src="https://i.pravatar.cc/150?u=admin" alt="Admin" className="w-full h-full object-cover" />
            </div>
          </div>
        </header>

        {/* Scrollable Content */}
        <div className="flex-1 overflow-y-auto p-8">
          
          {/* Customer Profile Card */}
          <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex items-center justify-between mb-6">
            <div className="flex items-center gap-6">
              <div className="w-20 h-20 rounded-full bg-slate-100 border-4 border-white shadow-md overflow-hidden shrink-0">
                <img src="https://i.pravatar.cc/150?u=jubaer" alt="Customer" className="w-full h-full object-cover" />
              </div>
              <div>
                <div className="flex items-center gap-3 mb-4">
                  <h3 className="text-2xl font-bold text-slate-900">Jubaer Riyad</h3>
                  <span className="px-2.5 py-1 text-xs font-semibold text-teal-600 bg-teal-50 rounded-full border border-teal-100">New Customer</span>
                </div>
                <div className="flex gap-12 text-sm">
                  <div>
                    <p className="text-slate-400 mb-1">Email address:</p>
                    <p className="font-medium">Jubaer@musemind.agency</p>
                  </div>
                  <div>
                    <p className="text-slate-400 mb-1">Phone number:</p>
                    <p className="font-medium">(451) 555-4759</p>
                  </div>
                  <div>
                    <p className="text-slate-400 mb-1">House location:</p>
                    <p className="font-medium">67B Gregorio Grove, Jaskolskiville</p>
                  </div>
                </div>
              </div>
            </div>
            
            <div className="bg-slate-50 p-4 rounded-xl border border-slate-100 min-w-[240px]">
              <p className="text-xs text-slate-500 mb-3 font-medium">Representative</p>
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-full bg-slate-200 overflow-hidden">
                  <img src="https://i.pravatar.cc/150?u=alan" alt="Rep" className="w-full h-full object-cover" />
                </div>
                <div>
                  <p className="font-bold text-slate-900 text-sm">Alan Shopon</p>
                  <p className="text-xs text-slate-500">Sr. Executive</p>
                </div>
              </div>
            </div>
          </div>

          {/* Stats Cards Row */}
          <div className="grid grid-cols-4 gap-6 mb-8">
            {/* Card 1 */}
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-500 font-medium text-sm mb-4">
                <div className="w-6 h-6 rounded-full bg-amber-50 flex items-center justify-center">
                  <span className="text-amber-500 text-xs">$</span>
                </div>
                Total estimate
              </div>
              <div className="flex justify-between items-end mb-4">
                <div>
                  <h4 className="text-2xl font-bold">22.42k</h4>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> ACCEPTED
                  </div>
                </div>
                <div>
                  <h4 className="text-2xl font-bold text-slate-700">15.52k</h4>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400 font-medium">
                    <CircleDashed className="w-3.5 h-3.5 text-amber-500" /> PENDING
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-slate-50">
                <div className="flex items-center gap-1 text-xs text-slate-400">
                  <span className="flex items-center text-emerald-500 font-medium"><ArrowUpRight className="w-3 h-3 mr-0.5"/> 2.75%</span> Last month
                </div>
                <button className="text-xs font-semibold text-slate-400 hover:text-slate-600">View more</button>
              </div>
            </div>

            {/* Card 2 */}
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-500 font-medium text-sm mb-4">
                <div className="w-6 h-6 rounded-full bg-teal-50 flex items-center justify-center">
                  <Briefcase className="w-3.5 h-3.5 text-teal-500" />
                </div>
                Changes Order
              </div>
              <div className="flex justify-between items-end mb-4">
                <div>
                  <h4 className="text-2xl font-bold">24.47k</h4>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> ACCEPTED
                  </div>
                </div>
                <div>
                  <h4 className="text-2xl font-bold text-slate-700">34.64k</h4>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400 font-medium">
                    <CircleDashed className="w-3.5 h-3.5 text-amber-500" /> PENDING
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-slate-50">
                <div className="flex items-center gap-1 text-xs text-slate-400">
                  <span className="flex items-center text-rose-500 font-medium"><ArrowDownRight className="w-3 h-3 mr-0.5"/> 2.75%</span> Last month
                </div>
                <button className="text-xs font-semibold text-slate-400 hover:text-slate-600">View more</button>
              </div>
            </div>

            {/* Card 3 */}
            <div className="bg-white p-5 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between">
              <div className="flex items-center gap-2 text-slate-500 font-medium text-sm mb-4">
                <div className="w-6 h-6 rounded-full bg-rose-50 flex items-center justify-center">
                  <ListTodo className="w-3.5 h-3.5 text-rose-500" />
                </div>
                Invoices
              </div>
              <div className="flex justify-between items-end mb-4">
                <div>
                  <h4 className="text-2xl font-bold">17.92k</h4>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400 font-medium">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" /> PAID
                  </div>
                </div>
                <div>
                  <h4 className="text-2xl font-bold text-slate-700">12.34k</h4>
                  <div className="flex items-center gap-1.5 mt-1 text-xs text-slate-400 font-medium">
                    <CircleDashed className="w-3.5 h-3.5 text-amber-500" /> PENDING
                  </div>
                </div>
              </div>
              <div className="flex items-center justify-between pt-4 border-t border-slate-50">
                <div className="flex items-center gap-1 text-xs text-slate-400">
                  <span className="flex items-center text-emerald-500 font-medium"><ArrowUpRight className="w-3 h-3 mr-0.5"/> 2.75%</span> Last month
                </div>
                <button className="text-xs font-semibold text-slate-400 hover:text-slate-600">View more</button>
              </div>
            </div>

            {/* Card 4 - Overdue */}
            <div className="p-5 rounded-2xl shadow-md flex flex-col justify-center items-center text-white relative overflow-hidden" 
                 style={{background: 'linear-gradient(135deg, #74a89a 0%, #a4c9a8 100%)'}}>
              <p className="font-semibold text-teal-50 mb-1">Overdue</p>
              <h4 className="text-4xl font-bold tracking-tight mb-4">17.92k</h4>
              <button className="px-5 py-2 bg-white/20 hover:bg-white/30 backdrop-blur-sm rounded-lg text-sm font-semibold transition-colors border border-white/20 shadow-sm">
                View Details
              </button>
            </div>
          </div>

          {/* Table Section */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
            
            {/* Tabs */}
            <div className="flex items-center gap-8 px-6 border-b border-slate-100">
              <button className="py-4 text-sm font-semibold text-teal-700 border-b-2 border-teal-600">Documentation (120)</button>
              <button className="py-4 text-sm font-medium text-slate-400 hover:text-slate-600">Project (21)</button>
              <button className="py-4 text-sm font-medium text-slate-400 hover:text-slate-600">Photos</button>
              <button className="py-4 text-sm font-medium text-slate-400 hover:text-slate-600">Files (32)</button>
              <button className="py-4 text-sm font-medium text-slate-400 hover:text-slate-600">Project (12)</button>
            </div>

            {/* Toolbar */}
            <div className="p-6 flex items-center justify-between border-b border-slate-50">
              <div className="flex gap-4">
                <div className="relative">
                  <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
                  <input 
                    type="text" 
                    placeholder="Search document" 
                    className="pl-9 pr-4 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:border-teal-500 w-64"
                  />
                </div>
                <button className="flex items-center gap-2 px-4 py-2 border border-slate-200 rounded-lg text-sm font-medium text-slate-600 hover:bg-slate-50">
                  <ListTodo className="w-4 h-4" /> Sort by
                </button>
              </div>
              <button className="flex items-center gap-2 px-4 py-2 bg-white border border-teal-600 text-teal-600 rounded-lg text-sm font-semibold hover:bg-teal-50 transition-colors">
                Create document <ChevronDown className="w-4 h-4 ml-1" />
              </button>
            </div>

            {/* Table */}
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="text-xs font-semibold text-slate-400 uppercase tracking-wider border-b border-slate-100">
                  <th className="px-6 py-4 font-medium">Documents</th>
                  <th className="px-6 py-4 font-medium">Associated Project</th>
                  <th className="px-6 py-4 font-medium">Value</th>
                  <th className="px-6 py-4 font-medium">Balance</th>
                  <th className="px-6 py-4 font-medium">Status</th>
                  <th className="px-6 py-4 font-medium">Sent Date</th>
                  <th className="px-6 py-4 font-medium">Due date</th>
                  <th className="px-6 py-4 font-medium text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-50 text-sm">
                {tableData.map((row, idx) => (
                  <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-6 py-4 flex items-center gap-3">
                      <input type="checkbox" className="w-4 h-4 rounded border-slate-300 text-teal-600 focus:ring-teal-500" />
                      <span className="font-medium text-slate-600">{row.id}</span>
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-slate-200 overflow-hidden shrink-0">
                          <img src={`https://i.pravatar.cc/150?u=${row.email}`} alt="" />
                        </div>
                        <div>
                          <p className="font-medium text-slate-900">{row.name}</p>
                          <p className="text-xs text-slate-400">{row.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-4 font-medium text-slate-700">{row.value}</td>
                    <td className="px-6 py-4 font-medium text-slate-700">{row.balance}</td>
                    <td className="px-6 py-4">
                      <span className={`inline-flex px-2.5 py-1 rounded-full text-xs font-semibold ${getStatusColor(row.status)}`}>
                        {row.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-slate-500">{row.date}</td>
                    <td className="px-6 py-4 text-slate-500">{row.date}</td>
                    <td className="px-6 py-4 text-right">
                      <button className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-teal-500 text-white rounded-md text-xs font-semibold hover:bg-teal-600 transition-colors shadow-sm">
                        <Edit className="w-3.5 h-3.5" /> Edit
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

        </div>
      </main>
    </div>
  );
}

