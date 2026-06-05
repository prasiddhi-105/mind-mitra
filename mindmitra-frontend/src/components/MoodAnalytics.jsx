import React, { useState, useRef } from "react";

} from "recharts";
import jsPDF from "jspdf";
import html2canvas from "html2canvas";


  const [viewType, setViewType] = useState("weekly");
  const reportRef = useRef(null);

  const isWeekly = viewType === "weekly";

  };

  return (
    <div className="p-6 max-w-6xl mx-auto bg-gray-50 min-h-screen font-sans">

          <div className="bg-gray-100 p-1 rounded-lg flex items-center shadow-inner">
            <button
              onClick={() => setViewType("weekly")}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                isWeekly ? "bg-white text-blue-600 shadow-sm" : "text-gray-600 hover:text-gray-900"
              }`}
            >

            </button>
            <button
              onClick={() => setViewType("monthly")}
              className={`px-4 py-1.5 rounded-md text-sm font-medium transition-all ${
                !isWeekly ? "bg-white text-blue-600 shadow-sm" : "text-gray-600 hover:text-gray-900"
              }`}
            >

          </button>
        </div>
      </div>


          </span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">

            <div className="h-80 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={lineData} margin={{ top: 10, right: 20, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F3F4F6" />
                  <XAxis dataKey="name" stroke="#9CA3AF" fontSize={12} tickLine={false} />

                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>


            </div>
            <div className="h-56 w-full relative flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>

            <div className="grid grid-cols-2 gap-2 mt-4">
              {pieData.map((entry, index) => (
                <div key={index} className="flex items-center gap-2 text-sm text-gray-600">
                  <span className="w-3 h-3 rounded-full inline-block" style={{ backgroundColor: entry.color }}></span>
                  <span>{entry.name} ({entry.value})</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
